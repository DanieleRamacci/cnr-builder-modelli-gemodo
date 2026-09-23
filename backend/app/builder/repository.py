"""Repository helpers for the builder admin domain (model/version creation and workflow)."""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, PolicyDimensione, TipoDocumento

# Valore del filtro livello che seleziona i modelli generici, dove la colonna
# e' NULL. Serve un token esplicito perche' "assente" in un filtro significa
# gia' "non filtrare".
LIVELLO_GENERICO = "TUTTI"


def lista_modelli(
    db: Session,
    codice_contesto: str,
    *,
    offset: int,
    limit: int,
    codice_tipo_documento: str | None = None,
    integrazione_id: uuid.UUID | None = None,
    codice_tipologia: str | None = None,
    codice_categoria: str | None = None,
    lingua: str | None = None,
    livello_professionale: str | None = None,
    variante: str | None = None,
    stato_versione: str | None = None,
):
    """Modelli del contesto, filtrati lato server (007 FR-028).

    I filtri sono condizioni su colonne gia' esistenti, non richiedono il
    discovery. Devono stare qui e non nel client perche' la query e' paginata:
    filtrare dopo `limit` restituirebbe la pagina in mano invece dell'insieme.
    """
    query = (
        select(ModelloDocumento)
        .join(TipoDocumento, ModelloDocumento.tipo_documento_id == TipoDocumento.id)
        .where(TipoDocumento.codice_contesto == codice_contesto, ModelloDocumento.stato != "ELIMINATO")
    )
    if codice_tipo_documento is not None:
        query = query.where(TipoDocumento.codice == codice_tipo_documento)
    if integrazione_id is not None:
        query = query.where(TipoDocumento.integrazione_id == integrazione_id)
    if codice_tipologia is not None:
        query = query.where(ModelloDocumento.codice_tipologia == codice_tipologia)
    if codice_categoria is not None:
        query = query.where(ModelloDocumento.codice_categoria == codice_categoria)
    if lingua is not None:
        query = query.where(ModelloDocumento.lingua == lingua)
    if livello_professionale is not None:
        # "TUTTI" seleziona i modelli generici, dove la colonna e' NULL: senza
        # questo, un livello non valorizzato non sarebbe filtrabile affatto.
        query = query.where(
            ModelloDocumento.livello_professionale.is_(None)
            if livello_professionale == LIVELLO_GENERICO
            else ModelloDocumento.livello_professionale == livello_professionale
        )
    if variante is not None:
        query = query.where(ModelloDocumento.variante == variante)
    if stato_versione is not None:
        query = query.where(
            select(ModelloDocumentoVersione.id)
            .where(
                ModelloDocumentoVersione.modello_documento_id == ModelloDocumento.id,
                ModelloDocumentoVersione.stato == stato_versione,
            )
            .exists()
        )
    return list(db.scalars(
        query
        .options(joinedload(ModelloDocumento.tipo_documento), selectinload(ModelloDocumento.versioni))
        .order_by(ModelloDocumento.created_at.desc(), ModelloDocumento.id)
        .offset(offset).limit(limit)
    ))


def modello_con_campi(db: Session, modello_id):
    """Dettaglio di un modello con i campi di ogni versione, bozze incluse."""
    return db.scalar(select(ModelloDocumento)
        .where(ModelloDocumento.id == modello_id, ModelloDocumento.stato != "ELIMINATO")
        .options(
            joinedload(ModelloDocumento.tipo_documento),
            selectinload(ModelloDocumento.versioni).selectinload(ModelloDocumentoVersione.campi),
        ))


def policy_dimensioni(db: Session, tipo_documento_id) -> list[PolicyDimensione]:
    return list(db.scalars(select(PolicyDimensione)
        .where(PolicyDimensione.tipo_documento_id == tipo_documento_id)
        .order_by(PolicyDimensione.nome_dimensione)))


def salva_policy_dimensione(
    db: Session, *, tipo_documento_id, nome_dimensione: str, consente_valore_generico: bool, soggetto: str | None,
) -> tuple[PolicyDimensione, bool]:
    """Aggiorna la policy se esiste, altrimenti la crea. Mai due righe per lo stesso nome."""
    esistente = db.scalar(select(PolicyDimensione).where(
        PolicyDimensione.tipo_documento_id == tipo_documento_id,
        PolicyDimensione.nome_dimensione == nome_dimensione,
    ).with_for_update())
    if esistente is not None:
        esistente.consente_valore_generico = consente_valore_generico
        esistente.updated_at = datetime.now(timezone.utc)
        esistente.updated_by = soggetto
        db.flush()
        return esistente, False
    creata = PolicyDimensione(
        tipo_documento_id=tipo_documento_id, nome_dimensione=nome_dimensione,
        consente_valore_generico=consente_valore_generico, updated_by=soggetto,
    )
    db.add(creata)
    db.flush()
    return creata, True


def _prossimo_public_id(db: Session, model) -> int:
    massimo = db.scalar(select(func.max(model.public_id)))
    return (massimo or 0) + 1


def crea_modello(
    db: Session,
    *,
    modello_id: uuid.UUID,
    codice: str,
    nome: str,
    tipo_documento_id: uuid.UUID,
    codice_categoria: str,
    codice_tipologia: str | None,
    percorso_categorizzazione: list[str],
    variante: str,
    lingua: str,
    livello_professionale: str | None,
    derivato_da_modello_id: uuid.UUID | None = None,
) -> ModelloDocumento:
    modello = ModelloDocumento(
        id=modello_id,
        public_id=_prossimo_public_id(db, ModelloDocumento),
        tipo_documento_id=tipo_documento_id,
        codice_categoria=codice_categoria,
        codice_tipologia=codice_tipologia,
        percorso_categorizzazione=percorso_categorizzazione,
        codice=codice,
        nome=nome,
        variante=variante,
        lingua=lingua,
        livello_professionale=livello_professionale,
        derivato_da_modello_id=derivato_da_modello_id,
        stato="ATTIVA",
    )
    db.add(modello)
    db.flush()
    return modello


def get_modello(db: Session, modello_id: uuid.UUID) -> ModelloDocumento | None:
    stmt = (
        select(ModelloDocumento)
        .options(
            joinedload(ModelloDocumento.tipo_documento),
        )
        .where(ModelloDocumento.id == modello_id, ModelloDocumento.stato != "ELIMINATO")
    )
    return db.scalar(stmt)


def crea_versione(
    db: Session,
    *,
    modello_documento_id: uuid.UUID,
    campi: list[ModelloCampoRichiesto],
    formato_documentale: str = "GEMODO_DOCUMENT_V1",
    struttura_documentale: dict | None = None,
) -> ModelloDocumentoVersione:
    numero_versione = (
        db.scalar(
            select(func.max(ModelloDocumentoVersione.versione)).where(
                ModelloDocumentoVersione.modello_documento_id == modello_documento_id
            )
        )
        or 0
    ) + 1
    versione = ModelloDocumentoVersione(
        id=uuid.uuid4(),
        public_id=_prossimo_public_id(db, ModelloDocumentoVersione),
        modello_documento_id=modello_documento_id,
        versione=numero_versione,
        stato="BOZZA",
        formato_documentale=formato_documentale,
        struttura_documentale=deepcopy(struttura_documentale) if struttura_documentale is not None else {},
    )
    db.add(versione)
    db.flush()
    for campo in campi:
        campo.modello_versione_id = versione.id
        db.add(campo)
    db.flush()
    return versione


def get_ultima_versione_con_campi(
    db: Session, modello_id: uuid.UUID,
) -> ModelloDocumentoVersione | None:
    stmt = (
        select(ModelloDocumentoVersione)
        .where(ModelloDocumentoVersione.modello_documento_id == modello_id)
        .options(selectinload(ModelloDocumentoVersione.campi))
        .order_by(ModelloDocumentoVersione.versione.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def get_edizione_derivata(
    db: Session, modello_origine_id: uuid.UUID, lingua: str,
) -> ModelloDocumento | None:
    return db.scalar(select(ModelloDocumento).where(
        ModelloDocumento.derivato_da_modello_id == modello_origine_id,
        ModelloDocumento.lingua == lingua,
        ModelloDocumento.stato != "ELIMINATO",
    ))


def clona_campi(versione: ModelloDocumentoVersione) -> list[ModelloCampoRichiesto]:
    return [ModelloCampoRichiesto(
        id=uuid.uuid4(),
        codice=campo.codice,
        etichetta=campo.etichetta,
        descrizione=campo.descrizione,
        tipo_dato=campo.tipo_dato,
        obbligatorio=campo.obbligatorio,
        lingua=campo.lingua,
        ordine=campo.ordine,
        formato=campo.formato,
        valore_default=campo.valore_default,
        opzioni=deepcopy(campo.opzioni),
        validazione=deepcopy(campo.validazione),
    ) for campo in versione.campi]


def get_versione(db: Session, versione_id: uuid.UUID) -> ModelloDocumentoVersione | None:
    stmt = (
        select(ModelloDocumentoVersione)
        .options(joinedload(ModelloDocumentoVersione.modello))
        .where(ModelloDocumentoVersione.id == versione_id)
    )
    return db.scalar(stmt)


def get_versione_pubblicata_corrente(
    db: Session,
    *,
    tipo_documento_id: uuid.UUID,
    percorso_categorizzazione: list[str],
    variante: str,
    lingua: str,
    livello_professionale: str | None,
    escludi_versione_id: uuid.UUID,
) -> ModelloDocumentoVersione | None:
    stmt = (
        select(ModelloDocumentoVersione)
        .join(ModelloDocumento, ModelloDocumentoVersione.modello_documento_id == ModelloDocumento.id)
        .where(
            ModelloDocumento.tipo_documento_id == tipo_documento_id,
            ModelloDocumento.percorso_categorizzazione == percorso_categorizzazione,
            ModelloDocumento.variante == variante,
            ModelloDocumento.lingua == lingua,
            ModelloDocumento.livello_professionale == livello_professionale,
            ModelloDocumentoVersione.stato == "PUBBLICATO",
            ModelloDocumentoVersione.id != escludi_versione_id,
        )
    )
    return db.scalar(stmt)


def transizione_stato(
    db: Session,
    versione: ModelloDocumentoVersione,
    *,
    nuovo_stato: str,
) -> ModelloDocumentoVersione:
    versione.stato = nuovo_stato
    versione.updated_at = datetime.now(timezone.utc)
    if nuovo_stato == "PUBBLICATO":
        versione.pubblicato_at = datetime.now(timezone.utc)
        versione.pubblicato_il = datetime.now(timezone.utc)
    db.add(versione)
    db.flush()
    return versione
