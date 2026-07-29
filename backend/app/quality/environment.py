"""Static validation for AmbienteLocale / ServizioLocale definitions.

Encodes the invariants an environment definition itself must satisfy (spec 009,
data-model.md), independent of whether the described services are actually reachable
right now - reachability is the concern of ``environment_verifier.py``.
"""

from __future__ import annotations

from app.quality.errors import ContrattoNonValidoError
from app.quality.schemas import AmbienteLocale, CategoriaServizio, ServizioLocale

# FR-001 / data-model.md: "deve includere almeno backend, frontend, PostgreSQL,
# Keycloak e documentale mock".
SERVIZI_MINIMI_RICHIESTI: set[str] = {"backend", "frontend", "postgres", "keycloak", "documentale-mock"}

# L'ambiente non deve richiedere accesso a GEBAN reale (data-model.md); il nome di
# servizio "geban" (o varianti con suffisso "-reale") non e' mai ammesso, a differenza
# di "mock-geban" che e' lo stand-in di sviluppo.
NOMI_SERVIZIO_NON_AMMESSI: set[str] = {"geban", "geban-reale"}


def validate_servizio_locale(servizio: ServizioLocale) -> None:
    violazioni: list[str] = []

    if servizio.nome.strip().lower() in NOMI_SERVIZIO_NON_AMMESSI:
        violazioni.append(
            f"servizio '{servizio.nome}' non ammesso: l'ambiente locale non deve dipendere da GEBAN reale"
        )
    if servizio.obbligatorio and not servizio.healthcheck.strip():
        violazioni.append(f"servizio '{servizio.nome}': obbligatorio ma senza comando/endpoint di healthcheck")
    if servizio.categoria == CategoriaServizio.MOCK and servizio.obbligatorio:
        violazioni.append(
            f"servizio mock '{servizio.nome}' non dovrebbe essere obbligatorio per l'ambiente minimo"
        )

    if violazioni:
        raise ContrattoNonValidoError(servizio.nome, violazioni)


def validate_ambiente_locale(ambiente: AmbienteLocale) -> None:
    violazioni: list[str] = []

    nomi_presenti = {s.nome for s in ambiente.servizi}
    mancanti = SERVIZI_MINIMI_RICHIESTI - nomi_presenti
    if mancanti:
        violazioni.append(f"servizi minimi mancanti dall'ambiente: {', '.join(sorted(mancanti))}")

    if not ambiente.documentazione_setup.strip():
        violazioni.append("documentazione_setup mancante")

    for servizio in ambiente.servizi:
        try:
            validate_servizio_locale(servizio)
        except ContrattoNonValidoError as exc:
            violazioni.extend(exc.violazioni)

    if violazioni:
        raise ContrattoNonValidoError(ambiente.id, violazioni)


def ambiente_locale_default() -> AmbienteLocale:
    """The canonical local-dev environment definition (FR-001, US1 Independent Test).

    ``frontend`` and ``mock-geban`` are not marked ``obbligatorio``: the frontend has no
    implementation yet (placeholder from T005/T006, real healthcheck lands with spec
    007 - see ``infra/local/frontend/README.md``) and the mock is a development/test
    tool for User Story 2, not part of the FR-001 minimum setup (backend, frontend,
    database, documentale mock, identity).
    """

    return AmbienteLocale(
        id="local-dev",
        servizi=[
            ServizioLocale(
                nome="backend",
                categoria=CategoriaServizio.APP,
                healthcheck="GET /health",
                obbligatorio=True,
            ),
            ServizioLocale(
                nome="frontend",
                categoria=CategoriaServizio.APP,
                healthcheck="GET http://localhost:4200/",
                obbligatorio=False,
            ),
            ServizioLocale(
                nome="postgres",
                categoria=CategoriaServizio.DATABASE,
                healthcheck="pg_isready -U ${POSTGRES_USER}",
                obbligatorio=True,
            ),
            ServizioLocale(
                nome="keycloak",
                categoria=CategoriaServizio.IDENTITA,
                healthcheck="GET ${KEYCLOAK_ISSUER_URL}/.well-known/openid-configuration",
                obbligatorio=True,
            ),
            ServizioLocale(
                nome="documentale-mock",
                categoria=CategoriaServizio.STORAGE,
                healthcheck="GET http://localhost:9000/health",
                dipendenze=[],
                obbligatorio=True,
            ),
            ServizioLocale(
                nome="mock-geban",
                categoria=CategoriaServizio.MOCK,
                healthcheck="python mock-geban/scenario_runner.py --scenario E2E-001",
                dipendenze=["backend"],
                obbligatorio=False,
            ),
        ],
        stato_atteso=["backend", "postgres", "keycloak", "documentale-mock"],
        documentazione_setup="specs/009-fondamenta-mock-test-qualita/quickstart.md",
    )
