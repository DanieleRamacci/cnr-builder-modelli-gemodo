"""Local adapter: reads GEMODO's own catalog tables directly.

Used for a self-service tipo documento (GEMODO is the owner) and, tonight,
also for BANDO_CONCORSO's real seeded data ahead of AdapterHTTP existing
(specs/010-configurazione-cataloghi-integrazioni, not implemented yet). No
network call, no cache needed: the tables it reads are already local.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.catalog import repository
from app.discovery.schemas import CampoDisponibile, ProfiloDisponibile, TipologiaDisponibile


class AdapterLocale:
    def __init__(self, db: Session) -> None:
        self.db = db

    def tipologie_disponibili(self, codice_tipo_documento: str) -> list[TipologiaDisponibile]:
        rows = repository.list_classificazione_by_tipo_codice(self.db, codice_tipo_documento)
        profili_per_tipologia: dict[str, list[ProfiloDisponibile]] = defaultdict(list)
        descrizione_tipologia: dict[str, str] = {}
        ordine_tipologie: list[str] = []
        for row in rows:
            tipologia = row.tipologia_bando_sol
            categoria = row.categoria_documento
            if tipologia.codice not in descrizione_tipologia:
                descrizione_tipologia[tipologia.codice] = tipologia.descrizione
                ordine_tipologie.append(tipologia.codice)
            profili_per_tipologia[tipologia.codice].append(
                ProfiloDisponibile(codice=categoria.codice, descrizione=categoria.nome)
            )
        return [
            TipologiaDisponibile(
                codice=codice,
                descrizione=descrizione_tipologia[codice],
                profili=tuple(profili_per_tipologia[codice]),
            )
            for codice in ordine_tipologie
        ]

    def campi_disponibili(self, codice_tipo_documento: str) -> list[CampoDisponibile]:
        registri = repository.list_registri_contratti_attivi_by_tipo_codice(self.db, codice_tipo_documento)
        campi: dict[str, CampoDisponibile] = {}
        for registro in registri:
            for raw in registro.campi:
                campo = CampoDisponibile(
                    codice=raw["codice"],
                    etichetta=raw["etichetta"],
                    tipo_dato=raw["tipo_dato"],
                    obbligatorio=raw["obbligatorio"],
                    lingua=raw.get("lingua", "IT"),
                    ordine=raw["ordine"],
                    validazione=raw.get("validazione"),
                )
                campi[campo.codice] = campo
        return sorted(campi.values(), key=lambda campo: campo.ordine)
