"""Repository helpers for the builder admin domain (model/version creation and workflow)."""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, PolicyDimensione, TipoDocumento

# Valore del filtro livello che seleziona i modelli generici, cioe' quelli che
# non valorizzano la dimensione. Serve un token esplicito perche' "assente" in
# un filtro significa gia' "non filtrare".
LIVELLO_GENERICO = "TUTTI"

# 011 T054: il nome della dimensione del livello e' uniformato a quello della
# colonna che sostituisce e del campo di contratto. Tenere due nomi avrebbe
# cablato la traduzione fra loro.
NOME_LIVELLO = "livello_professionale"


def _filtro_dimensione(nome: str, valore: str):
    """Condizione sul valore di una dimensione dentro il documento `dimensioni`.

    `LIVELLO_GENERICO` seleziona i modelli che **non** valorizzano la dimensione:
    con le colonne era `IS NULL`, con il documento e' l'assenza della chiave, che
    e' il modo in cui 011 FR-006 esprime "dimensione non valorizzata".
    """
    if valore == LIVELLO_GENERICO:
        return ~ModelloDocumento.dimensioni.has_key(nome)  # noqa: W601 - operatore JSONB, non dict.has_key
    return ModelloDocumento.dimensioni[nome].astext == valore


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
    ricerca: str | None = None,
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
        query = query.where(_filtro_dimensione("lingua", lingua))
    if livello_professionale is not None:
        query = query.where(_filtro_dimensione(NOME_LIVELLO, livello_professionale))
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
    if ricerca:
        # Sottostringa su nome e codice. `ilike` non usa indice: accettabile con
        # modelli nell'ordine delle centinaia, da rivedere se crescessero di
        # ordini di grandezza (007 FR-028, nota sulla scala).
        schema = f"%{ricerca.strip()}%"
        query = query.where(
            ModelloDocumento.nome.ilike(schema) | ModelloDocumento.codice.ilike(schema)
        )
    return list(db.scalars(
        query
        .options(joinedload(ModelloDocumento.tipo_documento), selectinload(ModelloDocumento.versioni))
        .order_by(ModelloDocumento.created_at.desc(), ModelloDocumento.id)
        .offset(offset).limit(limit)
    ))


def voci_filtro(db: Session, codice_contesto: str) -> dict[str, list[str]]:
    """Valori selezionabili nei filtri, ricavati dai modelli esistenti (007 FR-028).

    Non dall'albero discovery, per due ragioni. L'elenco modelli funziona anche
    quando l'integrazione e' irraggiungibile - il contratto lo dichiara, "non
    richiede discovery online" - e prendere le voci di la' legherebbe la pagina
    alla disponibilita' di GEBAN per riempire due tendine. Inoltre l'albero
    offre ogni combinazione possibile, comprese quelle senza alcun modello:
    tendine piene di voci che danno sempre elenco vuoto.

    Il livello generico e' esposto come `LIVELLO_GENERICO`, perche' nel filtro
    "assente" significa gia' "non filtrare".
    """
    def distinti(colonna) -> list[str]:
        query = (
            select(colonna)
            # Lato sinistro esplicito: selezionando una colonna di TipoDocumento
            # SQLAlchemy non saprebbe da dove partire per il join.
            .select_from(ModelloDocumento)
            .join(TipoDocumento, ModelloDocumento.tipo_documento_id == TipoDocumento.id)
            .where(
                TipoDocumento.codice_contesto == codice_contesto,
                ModelloDocumento.stato != "ELIMINATO",
            )
            .distinct()
        )
        return sorted(valore for valore in db.scalars(query) if valore is not None)

    def distinti_dimensione(nome: str) -> list[str]:
        """Valori distinti di una dimensione, letti dentro il documento JSONB.

        Sostituisce il `DISTINCT` su colonna: e' il costo accettato di
        DEC-011-PERSISTENZA-DIMENSIONI, ed e' circoscritto a questa funzione.
        """
        query = (
            select(ModelloDocumento.dimensioni[nome].astext)
            .select_from(ModelloDocumento)
            .join(TipoDocumento, ModelloDocumento.tipo_documento_id == TipoDocumento.id)
            .where(
                TipoDocumento.codice_contesto == codice_contesto,
                ModelloDocumento.stato != "ELIMINATO",
            )
            .distinct()
        )
        return sorted(valore for valore in db.scalars(query) if valore is not None)

    def esiste_senza_dimensione(nome: str) -> bool:
        return db.scalar(
            select(ModelloDocumento.id)
            .join(TipoDocumento, ModelloDocumento.tipo_documento_id == TipoDocumento.id)
            .where(
                TipoDocumento.codice_contesto == codice_contesto,
                ModelloDocumento.stato != "ELIMINATO",
                ~ModelloDocumento.dimensioni.has_key(nome),  # noqa: W601 - operatore JSONB
            )
            .limit(1)
        ) is not None

    livelli = distinti_dimensione(NOME_LIVELLO)
    return {
        "codici_tipo_documento": distinti(TipoDocumento.codice),
        "codici_tipologia": distinti(ModelloDocumento.codice_tipologia),
        "codici_categoria": distinti(ModelloDocumento.codice_categoria),
        "lingue": distinti_dimensione("lingua"),
        "livelli_professionali": (
            [LIVELLO_GENERICO] + livelli if esiste_senza_dimensione(NOME_LIVELLO) else livelli
        ),
        "varianti": distinti(ModelloDocumento.variante),
    }


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


def _modelli_pubblicati(tipo_documento_id):
    return (
        select(ModelloDocumento)
        .join(
            ModelloDocumentoVersione,
            ModelloDocumentoVersione.modello_documento_id == ModelloDocumento.id,
        )
        .where(
            ModelloDocumento.tipo_documento_id == tipo_documento_id,
            ModelloDocumento.stato != "ELIMINATO",
            ModelloDocumentoVersione.stato == "PUBBLICATO",
        )
    )


def conta_modelli_pubblicati_con_dimensione(
    db: Session, tipo_documento_id, nome_dimensione: str
) -> int:
    """Conta i modelli pubblicati che valorizzano la dimensione richiesta."""
    return int(db.scalar(
        _modelli_pubblicati(tipo_documento_id)
        .with_only_columns(func.count(func.distinct(ModelloDocumento.id)))
        .where(ModelloDocumento.dimensioni.has_key(nome_dimensione))  # noqa: W601 - operatore JSONB
    ) or 0)


def modelli_pubblicati_senza_dimensione(
    db: Session, tipo_documento_id, nome_dimensione: str
) -> list[ModelloDocumento]:
    """I modelli pubblicati che **non** valorizzano la dimensione.

    Sono l'insieme opposto di `conta_modelli_pubblicati_con_dimensione`, ed e'
    quello che conta quando si chiude il generico: sono questi a restare senza
    un valore ammesso. Il conteggio mostrato prima del salvataggio guardava
    solo l'altro insieme, quindi annunciava zero proprio quando l'impatto
    c'era (DEC-011-POLICY-NON-INVALIDA-IL-PUBBLICATO).
    """
    return list(db.scalars(
        _modelli_pubblicati(tipo_documento_id)
        .where(~ModelloDocumento.dimensioni.has_key(nome_dimensione))  # noqa: W601 - operatore JSONB
        .distinct()
        .order_by(ModelloDocumento.codice)
    ))


def salva_policy_dimensione(
    db: Session, *, tipo_documento_id, nome_dimensione: str, consente_valore_generico: bool,
    soggetto: str | None, valore_default: str | None = None,
) -> tuple[PolicyDimensione, bool]:
    """Aggiorna la policy se esiste, altrimenti la crea. Mai due righe per lo stesso nome."""
    esistente = db.scalar(select(PolicyDimensione).where(
        PolicyDimensione.tipo_documento_id == tipo_documento_id,
        PolicyDimensione.nome_dimensione == nome_dimensione,
    ).with_for_update())
    if esistente is not None:
        esistente.consente_valore_generico = consente_valore_generico
        esistente.valore_default = valore_default
        esistente.updated_at = datetime.now(timezone.utc)
        esistente.updated_by = soggetto
        db.flush()
        return esistente, False
    creata = PolicyDimensione(
        tipo_documento_id=tipo_documento_id, nome_dimensione=nome_dimensione,
        consente_valore_generico=consente_valore_generico,
        valore_default=valore_default, updated_by=soggetto,
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
    dimensioni: dict[str, str],
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
        dimensioni=dict(dimensioni),
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
    db: Session, modello_origine_id: uuid.UUID, nome_dimensione: str, valore: str,
) -> ModelloDocumento | None:
    """L'edizione gia' derivata dall'origine per quel valore di dimensione.

    011 FR-013: la derivazione non e' piu' definita sulla lingua ma sulla
    dimensione. Il criterio che rende disponibile la funzione e' la policy -
    si deriva su una dimensione obbligatoria, perche' e' li' che il modello di
    origine ha certamente il valore di partenza - non il nome `lingua`.
    """
    return db.scalar(select(ModelloDocumento).where(
        ModelloDocumento.derivato_da_modello_id == modello_origine_id,
        ModelloDocumento.dimensioni[nome_dimensione].astext == valore,
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
    dimensioni: dict[str, str],
    escludi_versione_id: uuid.UUID,
) -> ModelloDocumentoVersione | None:
    """La versione pubblicata che occupa gia' lo stesso slot (011 FR-004).

    Lo slot passa da cinque colonne a quattro termini, di cui uno composito.
    `dimensioni` si confronta per **uguaglianza JSONB**, che PostgreSQL valuta
    per contenuto e non per ordine di inserimento delle chiavi: due modelli che
    differiscono anche per una sola dimensione occupano slot diversi e restano
    entrambi pubblicati, invece di archiviarsi a vicenda.

    `variante` resta un termine distinto e non entra in `dimensioni` (FR-012):
    la decide l'admin, mentre le dimensioni le dichiara l'integrazione.
    """
    stmt = (
        select(ModelloDocumentoVersione)
        .join(ModelloDocumento, ModelloDocumentoVersione.modello_documento_id == ModelloDocumento.id)
        .where(
            ModelloDocumento.tipo_documento_id == tipo_documento_id,
            ModelloDocumento.percorso_categorizzazione == percorso_categorizzazione,
            ModelloDocumento.variante == variante,
            ModelloDocumento.dimensioni == dimensioni,
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
