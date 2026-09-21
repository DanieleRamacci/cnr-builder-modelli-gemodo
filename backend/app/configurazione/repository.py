from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.catalog.models import ModelloDocumento, TipoDocumento
from app.common.errors import DomainError
from app.configurazione.models import DefinizioneStruttura, EndpointIntegrazione, Integrazione, SchemaDiscoveryGenerato

STATO_INATTIVA = "INATTIVA"


def conta_modelli(db: Session, tipo_documento_id) -> int:
    return db.scalar(
        select(func.count()).select_from(ModelloDocumento).where(ModelloDocumento.tipo_documento_id == tipo_documento_id)
    )


def tipo_documento(db: Session, codice: str, *, lock: bool = False):
    # Una riga INATTIVA (disattivata dall'admin, es. un duplicato abbandonato)
    # non deve mai contare per l'ambiguita': altrimenti "Disattiva" non
    # risolverebbe nulla per queste route (legge/scrive struttura), a
    # differenza del catalogo (001) che gia' filtra per stato.
    query = select(TipoDocumento).where(TipoDocumento.codice == codice, TipoDocumento.stato != STATO_INATTIVA)
    if lock:
        query = query.with_for_update()
    types = list(db.scalars(query.limit(2)))
    if len(types) > 1:
        raise DomainError("SORGENTE_AMBIGUA", "Indicare l'integrazione del tipo documento", status_code=409)
    return types[0] if types else None


def definizione_corrente(db: Session, tipo_id):
    return db.scalar(select(DefinizioneStruttura).where(
        DefinizioneStruttura.tipo_documento_id == tipo_id,
    ).order_by(DefinizioneStruttura.versione.desc()).limit(1))


def schema_discovery(db: Session, tipo_id, versione: int | None = None):
    query = select(SchemaDiscoveryGenerato).where(SchemaDiscoveryGenerato.tipo_documento_id == tipo_id)
    if versione is not None:
        query = query.where(SchemaDiscoveryGenerato.versione == versione)
    return db.scalar(query.order_by(SchemaDiscoveryGenerato.versione.desc()).limit(1))


def endpoint(db: Session, integrazione_id, *, lock: bool = False):
    if integrazione_id is None:
        return None
    query = select(EndpointIntegrazione).where(EndpointIntegrazione.integrazione_id == integrazione_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalar(query)


def integrazioni(db: Session):
    return list(db.scalars(select(Integrazione).order_by(Integrazione.codice)))


def integrazioni_connesse(db: Session) -> list[tuple[Integrazione, EndpointIntegrazione]]:
    righe = db.execute(
        select(Integrazione, EndpointIntegrazione)
        .join(EndpointIntegrazione, EndpointIntegrazione.integrazione_id == Integrazione.id)
        .where(EndpointIntegrazione.stato == "CONNESSO")
        .order_by(Integrazione.codice)
    ).all()
    return [(riga.Integrazione, riga.EndpointIntegrazione) for riga in righe]


def integrazione(db: Session, integrazione_id, *, lock: bool = False):
    query = select(Integrazione).where(Integrazione.id == integrazione_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return db.scalar(query)


def prossima_versione_schema(db: Session, tipo_id):
    return (db.scalar(select(func.max(SchemaDiscoveryGenerato.versione)).where(
        SchemaDiscoveryGenerato.tipo_documento_id == tipo_id,
    )) or 0) + 1


def dashboard(db: Session):
    # PostgreSQL DISTINCT ON selects the latest revisions in one aggregate query.
    definition = aliased(DefinizioneStruttura, select(DefinizioneStruttura).distinct(
        DefinizioneStruttura.tipo_documento_id,
    ).order_by(DefinizioneStruttura.tipo_documento_id, DefinizioneStruttura.versione.desc()).subquery())
    schema = aliased(SchemaDiscoveryGenerato, select(SchemaDiscoveryGenerato).distinct(
        SchemaDiscoveryGenerato.tipo_documento_id,
    ).order_by(SchemaDiscoveryGenerato.tipo_documento_id, SchemaDiscoveryGenerato.versione.desc()).subquery())
    return db.execute(select(TipoDocumento, definition, schema, EndpointIntegrazione)
                      .outerjoin(definition, definition.tipo_documento_id == TipoDocumento.id)
                      .outerjoin(schema, schema.tipo_documento_id == TipoDocumento.id)
                      .outerjoin(EndpointIntegrazione, EndpointIntegrazione.integrazione_id == TipoDocumento.integrazione_id)
                      .where(TipoDocumento.stato != STATO_INATTIVA)
                      .order_by(TipoDocumento.codice)).all()
