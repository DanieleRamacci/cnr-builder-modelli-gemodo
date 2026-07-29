"""Guard rejecting mock GEBAN scenarios that bypass public GEMODO contracts (FR-012).

The mock GEBAN must exercise exactly the operations GEBAN itself would call -
catalogo, campi/schema, validazione, generazione, stato, download - never internal
builder or database shortcuts
(``specs/009-fondamenta-mock-test-qualita/contracts/mock-geban-scenarios.yaml``,
``coverage_requirements``).
"""

from __future__ import annotations

from enum import Enum

from app.quality.errors import ContrattoNonValidoError


class OperazionePubblica(str, Enum):
    """The only operations mock GEBAN (or its scenario runner) is allowed to call."""

    CATALOGO_MODELLI = "catalogo_modelli"
    CAMPI_RICHIESTI = "campi_richiesti"
    VALIDA_PAYLOAD = "valida_payload"
    GENERA_DOCUMENTO = "genera_documento"
    STATO_GENERAZIONE = "stato_generazione"
    DOWNLOAD_DOCUMENTO = "download_documento"


# Frammenti la cui presenza in un riferimento/descrittore di uno step indica una
# scorciatoia interna (accesso diretto a builder/database) invece di un'operazione del
# contratto pubblico.
NOMI_VIETATI: tuple[str, ...] = (
    "db.",
    "database",
    " sql",
    "orm",
    ".session",
    "sqlalchemy",
    "internal",
    "interno",
    "repository",
    "bypass",
    "diretto",
)


def assert_operazione_pubblica(nome_operazione: str) -> OperazionePubblica:
    """Raise unless ``nome_operazione`` is one of the public GEMODO contract operations."""

    try:
        return OperazionePubblica(nome_operazione)
    except ValueError as exc:
        raise ContrattoNonValidoError(
            nome_operazione,
            [f"'{nome_operazione}' non e' un'operazione del contratto pubblico GEMODO"],
        ) from exc


def assert_no_internal_shortcut(step_descrittore: str) -> None:
    """Raise if a scenario step descriptor references an internal/database shortcut."""

    normalizzato = f" {step_descrittore.strip().lower()} "
    trovati = [nome for nome in NOMI_VIETATI if nome in normalizzato]
    if trovati:
        raise ContrattoNonValidoError(
            step_descrittore,
            [f"riferimento non ammesso a scorciatoia interna/database: {', '.join(trovati)}"],
        )
