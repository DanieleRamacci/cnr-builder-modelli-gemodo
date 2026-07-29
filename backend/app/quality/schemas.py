"""Typed domain models for the quality readiness entities of feature 009.

These models capture the *shape* of the entities documented in
``specs/009-fondamenta-mock-test-qualita/data-model.md``. They intentionally do not
enforce cross-field business rules that depend on runtime context (for example "a
seed must not contain sensitive data" or "a critical decision must be resolved
before implementation") - those rules live in the dedicated validation helpers
(``environment.py``, ``seed_demo.py``, ``integration_profile.py``,
``document_model.py``, ``decision.py``, ``coverage.py``, ``scenario.py``) and raise
the shared error types from ``errors.py``. Keeping the two concerns separate lets
callers distinguish "the manifest is malformed" (a Pydantic ``ValidationError``) from
"the manifest is well-formed but violates a quality rule" (a ``QualityError``
subclass).

The manifest-level contract in
``specs/009-fondamenta-mock-test-qualita/contracts/quality-readiness-contract.yaml``
is validated generically against its own declared sections/fields/rules by
``manifest_loader.py`` and is not hard-coded as a Pydantic model here, so that the
contract file remains the single source of truth for the readiness gate.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class QualityBaseModel(BaseModel):
    """Shared strict base: unknown fields signal a malformed/typo'd manifest."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# AmbienteLocale / ServizioLocale / VerificaAmbiente
# ---------------------------------------------------------------------------


class ProfiloAmbiente(str, Enum):
    MINIMO = "MINIMO"
    COMPLETO = "COMPLETO"
    CI = "CI"


class CategoriaServizio(str, Enum):
    APP = "APP"
    DATABASE = "DATABASE"
    IDENTITA = "IDENTITA"
    STORAGE = "STORAGE"
    MOCK = "MOCK"
    DOCS = "DOCS"


class ServizioLocale(QualityBaseModel):
    """Componente dell'ambiente locale (backend, frontend, postgres, ...)."""

    nome: str
    categoria: CategoriaServizio
    healthcheck: str
    dipendenze: list[str] = Field(default_factory=list)
    obbligatorio: bool = True


class AmbienteLocale(QualityBaseModel):
    """Insieme dei servizi minimi necessari per sviluppo e verifica."""

    id: str = "local-dev"
    profilo: ProfiloAmbiente = ProfiloAmbiente.MINIMO
    servizi: list[ServizioLocale]
    stato_atteso: list[str] = Field(default_factory=list)
    documentazione_setup: str


class EsitoVerifica(str, Enum):
    PASS_ = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"


class ProblemaVerifica(QualityBaseModel):
    """Singolo problema rilevato durante la verifica ambiente."""

    servizio: str
    tipo: str = Field(description="'prerequisito_mancante' o 'errore_applicativo'")
    dettaglio: str


class VerificaAmbiente(QualityBaseModel):
    """Risultato del controllo ambiente."""

    id: str
    ambiente_id: str
    timestamp: datetime
    servizi_verificati: list[str]
    esito: EsitoVerifica
    problemi: list[ProblemaVerifica] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SeedDemo
# ---------------------------------------------------------------------------


class TipoSeedDemo(str, Enum):
    CATALOGO = "CATALOGO"
    MODELLO = "MODELLO"
    SEZIONI = "SEZIONI"
    PAYLOAD = "PAYLOAD"
    UTENTI_RUOLI = "UTENTI_RUOLI"
    GENERAZIONE = "GENERAZIONE"


class SeedDemo(QualityBaseModel):
    """Dati iniziali ripetibili per mock e test."""

    id: str
    nome: str
    tipo: TipoSeedDemo
    marcatura_demo: str
    spec_owner: str
    resettable: bool = True
    dati_sensibili: bool = False


# ---------------------------------------------------------------------------
# ScenarioEndToEnd / MatriceCopertura
# ---------------------------------------------------------------------------


class PrioritaScenario(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TipoScenario(str, Enum):
    VALIDO = "VALIDO"
    ERRORE_VALIDAZIONE = "ERRORE_VALIDAZIONE"
    IDEMPOTENZA = "IDEMPOTENZA"
    CONFLITTO = "CONFLITTO"
    FALLIMENTO = "FALLIMENTO"
    AUTORIZZAZIONE = "AUTORIZZAZIONE"


class ScenarioEndToEnd(QualityBaseModel):
    """Flusso verificabile che attraversa piu' feature."""

    id: str
    nome: str
    priorita: PrioritaScenario
    tipo: TipoScenario
    spec_coinvolte: list[str] = Field(default_factory=list)
    requisiti_coperti: list[str] = Field(default_factory=list)
    contratti_coinvolti: list[str] = Field(default_factory=list)
    expected_outcome: list[str] = Field(default_factory=list)


class StatoCopertura(str, Enum):
    DA_COPRIRE = "DA_COPRIRE"
    COPERTO = "COPERTO"
    BLOCCATO = "BLOCCATO"


class MatriceCopertura(QualityBaseModel):
    """Collegamento tra requisiti, scenari, contratti e spec owner."""

    id: str
    spec_owner: str
    requirement_id: str
    scenario_id: str
    contract_ref: str
    stato: StatoCopertura
    note: str | None = None


# ---------------------------------------------------------------------------
# DecisioneAperta
# ---------------------------------------------------------------------------


class StatoDecisione(str, Enum):
    APERTA = "APERTA"
    ASSUNTA_PROVVISORIA = "ASSUNTA_PROVVISORIA"
    CONFERMATA = "CONFERMATA"
    SOSPESA = "SOSPESA"


class FaseBloccante(str, Enum):
    SPEC = "SPEC"
    PLAN = "PLAN"
    TASKS = "TASKS"
    IMPLEMENTAZIONE = "IMPLEMENTAZIONE"
    NESSUNA = "NESSUNA"


class DecisioneAperta(QualityBaseModel):
    """Scelta progettuale da confermare."""

    id: str
    titolo: str
    owner_spec: str
    spec_interessate: list[str] = Field(default_factory=list)
    stato: StatoDecisione
    assunzione_provvisoria: str | None = None
    impatto: str | None = None
    fase_bloccante: FaseBloccante = FaseBloccante.NESSUNA
    data_ultima_revisione: date | None = None


# ---------------------------------------------------------------------------
# SistemaRichiedente / ClientApplicativo / ProfiloDiIntegrazione
# ---------------------------------------------------------------------------


class StatoSistemaRichiedente(str, Enum):
    ATTIVO = "ATTIVO"
    SOSPESO = "SOSPESO"
    ARCHIVIATO = "ARCHIVIATO"


class StatoClientApplicativo(str, Enum):
    ATTIVO = "ATTIVO"
    SOSPESO = "SOSPESO"
    DA_CONFERMARE = "DA_CONFERMARE"


class ClientApplicativo(QualityBaseModel):
    """Identita' tecnica riconosciuta da Keycloak, associata a sistemi richiedenti."""

    client_id: str
    audience_attesa: str
    ruoli_claim_richiesti: list[str] = Field(default_factory=list)
    sistemi_abilitati: list[str] = Field(default_factory=list)
    stato: StatoClientApplicativo = StatoClientApplicativo.DA_CONFERMARE
    gestisce_credenziali: bool = False


class StatoProfiloIntegrazione(str, Enum):
    BOZZA = "BOZZA"
    ATTIVO = "ATTIVO"
    SOSPESO = "SOSPESO"
    ARCHIVIATO = "ARCHIVIATO"


class PermessoOperativo(str, Enum):
    CATALOGO = "catalogo"
    VALIDAZIONE = "validazione"
    GENERAZIONE_BOZZA = "generazione_bozza"
    GENERAZIONE_UFFICIALE = "generazione_ufficiale"
    STATO = "stato"
    DOWNLOAD = "download"


class ProfiloDiIntegrazione(QualityBaseModel):
    """Configurazione applicativa versionata che collega sistema, client e permessi."""

    codice: str
    sistema_richiedente: str
    versione: str
    stato: StatoProfiloIntegrazione = StatoProfiloIntegrazione.BOZZA
    client_ammessi: list[str] = Field(default_factory=list)
    tipi_documento_ammessi: list[str] = Field(default_factory=list)
    categorie_ammessi: list[str] = Field(default_factory=list)
    tipologie_ammessi: list[str] = Field(default_factory=list)
    modelli_versioni_ammessi: list[str] = Field(default_factory=list)
    contratti_dati_ammessi: list[str] = Field(default_factory=list)
    permessi_operativi: list[PermessoOperativo] = Field(default_factory=list)


class SistemaRichiedente(QualityBaseModel):
    """Applicazione esterna o modulo autorizzato a consumare i contratti GEMODO."""

    codice: str
    nome: str
    stato: StatoSistemaRichiedente = StatoSistemaRichiedente.ATTIVO
    client_applicativi: list[ClientApplicativo] = Field(default_factory=list)
    profili_integrazione: list[ProfiloDiIntegrazione] = Field(default_factory=list)
    spec_owner: str


# ---------------------------------------------------------------------------
# ModelloDocumentaleControllato / BloccoDocumento / AssetDocumento
# ---------------------------------------------------------------------------


class TipoBloccoDocumento(str, Enum):
    INTESTAZIONE = "INTESTAZIONE"
    LOGO = "LOGO"
    TITOLO = "TITOLO"
    PARAGRAFO = "PARAGRAFO"
    TABELLA = "TABELLA"
    COLONNE = "COLONNE"
    FIRMA = "FIRMA"
    FOOTER = "FOOTER"
    INTERRUZIONE_PAGINA = "INTERRUZIONE_PAGINA"


class PosizionamentoBlocco(str, Enum):
    TOP = "TOP"
    BODY = "BODY"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    BOTTOM_CENTER = "BOTTOM_CENTER"
    INLINE = "INLINE"
    COLUMN_LEFT = "COLUMN_LEFT"
    COLUMN_RIGHT = "COLUMN_RIGHT"


class BloccoDocumento(QualityBaseModel):
    """Elemento visuale ammesso nel modello documentale controllato."""

    id: str
    tipo: TipoBloccoDocumento
    contenuto: str | None = None
    posizionamento: PosizionamentoBlocco
    ordine: int = 0
    stile: str | None = None
    placeholder_usati: list[str] = Field(default_factory=list)
    regole_layout: dict[str, str] = Field(default_factory=dict)
    asset_ref: str | None = None
    colonne: list[str] = Field(default_factory=list)


class TipoAsset(str, Enum):
    LOGO = "LOGO"
    IMMAGINE = "IMMAGINE"
    TIMBRO = "TIMBRO"
    ALTRO = "ALTRO"


class AssetDocumento(QualityBaseModel):
    """Logo, immagine o risorsa grafica referenziata dal modello."""

    id: str
    tipo: TipoAsset
    nome: str
    versione: int
    storage_ref: str | None = None
    hash_file: str | None = None
    dimensioni_consentite: str | None = None
    spec_owner: str | None = None


class PaginaDocumento(QualityBaseModel):
    size: str = "A4"
    orientamento: str = "PORTRAIT"
    margini: str = "standard-cnr"


class ModelloDocumentaleControllato(QualityBaseModel):
    """Sorgente strutturata e versionata del layout/contenuto documentale."""

    id: str
    modello_versione_id: str
    formato: str = "GEMODO_DOCUMENT_V1"
    pagina: PaginaDocumento = Field(default_factory=PaginaDocumento)
    regioni: list[str] = Field(default_factory=list)
    blocchi: list[BloccoDocumento] = Field(default_factory=list)
    asset: list[AssetDocumento] = Field(default_factory=list)
    stili_ammessi: list[str] = Field(default_factory=list)
    placeholder_usati: list[str] = Field(default_factory=list)
    spec_owner: str
    contiene_html_libero: bool = False
    contiene_css_libero: bool = False
    contiene_script: bool = False


# ---------------------------------------------------------------------------
# ContrattoOpenAPI / EsempioAPI / CatalogoErroriFunzionali
# ---------------------------------------------------------------------------


class ApiScope(str, Enum):
    GEBAN = "GEBAN"
    BUILDER = "BUILDER"
    ADMIN = "ADMIN"
    INTERNO = "INTERNO"


class EsitoEsempioAPI(str, Enum):
    SUCCESSO = "successo"
    ERRORE_VALIDAZIONE = "errore_validazione"
    NON_AUTORIZZATO = "non_autorizzato"
    CONFLITTO = "conflitto"
    FALLIMENTO = "fallimento"


class EsempioAPI(QualityBaseModel):
    """Payload o risposta dimostrativa pubblicabile."""

    id: str
    contratto_openapi: str
    scenario: EsitoEsempioAPI
    request_ref: str | None = None
    response_ref: str
    dati_demo: bool = True
    contiene_segreti: bool = False
    contiene_dati_reali: bool = False


class DocumentazioneInterattiva(QualityBaseModel):
    """Swagger UI / ReDoc (o equivalenti) generati dalla stessa sorgente OpenAPI."""

    swagger_enabled: bool = False
    redoc_enabled: bool = False
    generated_from_same_openapi_source: bool = True


class ContrattoOpenAPI(QualityBaseModel):
    """Specifica versionata di una API pubblica, di integrazione o interna."""

    id: str
    nome: str
    versione: str
    file_ref: str
    api_scope: ApiScope
    endpoint_coperti: list[str] = Field(default_factory=list)
    schemi_coperti: list[str] = Field(default_factory=list)
    autenticazione: str = "bearer-jwt"
    autorizzazioni: list[str] = Field(default_factory=list)
    esempi: list[EsempioAPI] = Field(default_factory=list)
    catalogo_errori_ref: str
    documentazione_interattiva: DocumentazioneInterattiva = Field(
        default_factory=DocumentazioneInterattiva
    )
    spec_owner: str


class CatalogoErroriFunzionali(QualityBaseModel):
    """Elenco stabile degli errori pubblici esposti da API e scenari."""

    id: str
    api_scope: ApiScope
    codice: str
    http_status: int
    messaggio_pubblico: str
    condizione: str
    azione_suggerita: str
    audit_richiesto: bool = False


# ---------------------------------------------------------------------------
# PortaleDocumentazione / ReadinessOpenSourcePA
# ---------------------------------------------------------------------------


class PortaleDocumentazione(QualityBaseModel):
    """Documentazione navigabile generata dal repository (MkDocs)."""

    id: str
    generator_ref: str
    pagine: list[str] = Field(default_factory=list)
    fonti: list[str] = Field(default_factory=list)
    verifica_build: str


class ReadinessOpenSourcePA(QualityBaseModel):
    """Checklist e metadati necessari a pubblicazione e riuso da altre PA."""

    id: str
    licenza: str = "DA_CONFERMARE"
    readme_ref: str
    setup_ref: str
    sviluppo_ref: str
    produzione_ref: str
    architettura_ref: str
    sicurezza_ref: str
    contributing_ref: str
    security_policy_ref: str
    changelog_ref: str
    rilasci_ref: str
    contiene_segreti: bool = False
    contiene_dati_reali: bool = False
