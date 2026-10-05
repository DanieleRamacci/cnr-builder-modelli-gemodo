"""Registro attivita': solo per gli amministratori GEMODO (013 FR-011, FR-014)."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.attivita import repository
from app.attivita.schemas import EventoAttivitaResponse, RegistroAttivitaResponse
from app.common.security import PrincipalGEMODO
from app.configurazione.security import require_configurazione_admin
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/admin/attivita", tags=["registro-attivita"])
Admin = Annotated[PrincipalGEMODO, Depends(require_configurazione_admin)]

# L'esportazione e' un estratto, non un backup: oltre questo si restringe il filtro.
MASSIMO_CSV = 10_000
_COLONNE_CSV = (
    "quando", "categoria", "azione", "esito", "username", "soggetto", "client_id", "contesto",
    "oggetto_tipo", "oggetto_id", "oggetto_nome", "dettaglio",
)


def _filtro(
    da: date | None = Query(default=None, description="Dal giorno (incluso)"),
    a: date | None = Query(default=None, description="Al giorno (incluso)"),
    categoria: str | None = Query(default=None, description=", ".join(repository.CATEGORIE)),
    esito: str | None = Query(default=None),
    utente: str | None = Query(default=None, description="Username, id del token o client"),
    testo: str | None = Query(default=None, description="Oggetto, azione o dettaglio"),
) -> repository.FiltroAttivita:
    return repository.FiltroAttivita(
        da=datetime.combine(da, time.min, tzinfo=timezone.utc) if da else None,
        a=datetime.combine(a + timedelta(days=1), time.min, tzinfo=timezone.utc) if a else None,
        categoria=categoria, esito=esito, utente=utente, testo=testo,
    )


Filtro = Annotated[repository.FiltroAttivita, Depends(_filtro)]


@router.get("", response_model=RegistroAttivitaResponse)
def registro_attivita(
    _principal: Admin,
    filtro: Filtro,
    limite: int = Query(default=50, ge=1, le=200),
    salto: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> RegistroAttivitaResponse:
    righe = repository.elenco(db, filtro, limite=limite + 1, salto=salto)
    return RegistroAttivitaResponse(
        eventi=[EventoAttivitaResponse(**riga) for riga in righe[:limite]],
        altri=len(righe) > limite,
    )


def _cella(valore: object) -> str:
    testo = "" if valore is None else (
        json.dumps(valore, ensure_ascii=False) if isinstance(valore, dict)
        else valore.isoformat() if isinstance(valore, datetime) else str(valore)
    )
    # Un foglio di calcolo esegue le celle che cominciano cosi': nel registro
    # finiscono testi scritti da altri (nomi di modelli, chiavi esterne).
    return "'" + testo if testo[:1] in ("=", "+", "-", "@") else testo


@router.get(".csv")
def registro_attivita_csv(_principal: Admin, filtro: Filtro, db: Session = Depends(get_db)) -> Response:
    righe = repository.elenco(db, filtro, limite=MASSIMO_CSV, salto=0)
    uscita = io.StringIO()
    scrittore = csv.writer(uscita, delimiter=";")
    scrittore.writerow(_COLONNE_CSV)
    for riga in righe:
        scrittore.writerow([_cella(riga[colonna]) for colonna in _COLONNE_CSV])
    return Response(
        content="﻿" + uscita.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="registro-attivita.csv"'},
    )
