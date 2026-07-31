#!/usr/bin/env python3
"""Generate MkDocs pages from Spec Kit artifacts."""

from __future__ import annotations

import re
import shutil
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "specs"
DOCS_DIR = ROOT / "docs"
OUT_DIR = DOCS_DIR / "spec-kit"
PROJECT_MAP = DOCS_DIR / "project-map.md"
CONSTITUTION = ROOT / ".specify" / "memory" / "constitution.md"
README = ROOT / "README.md"
PROPOSAL = ROOT / "PROPOSTA-servizio-gestione-modelli-bando.md"
FEATURE_JSON = ROOT / ".specify" / "feature.json"

KNOWN_ARTIFACTS = [
    ("spec.md", "Spec"),
    ("checklists/requirements.md", "Checklist"),
    ("plan.md", "Plan"),
    ("tasks.md", "Tasks"),
    ("data-model.md", "Data model"),
    ("research.md", "Research"),
    ("quickstart.md", "Quickstart"),
    ("keycloak-jwt.md", "Keycloak JWT"),
    ("contracts/geban-catalog-api.openapi.yaml", "OpenAPI catalogo"),
    ("contracts/quality-readiness-contract.yaml", "Quality contract"),
    ("contracts/mock-geban-scenarios.yaml", "Mock scenarios"),
]


@dataclass
class SpecInfo:
    directory: Path
    slug: str
    title: str
    status: str
    area: str
    files: list[Path]
    checklist_done: tuple[int, int]
    tasks_done: tuple[int, int]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def first_match(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else default


def checkbox_counts(path: Path) -> tuple[int, int]:
    if not path.exists():
        return (0, 0)
    text = read_text(path)
    done = len(re.findall(r"^- \[x\]", text, flags=re.MULTILINE | re.IGNORECASE))
    total = len(re.findall(r"^- \[[ xX]\]", text, flags=re.MULTILINE))
    return (done, total)


def load_project_areas() -> dict[str, str]:
    if not PROJECT_MAP.exists():
        return {}

    areas: dict[str, str] = {}
    for line in read_text(PROJECT_MAP).splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        slug = cells[0].strip("`")
        area = cells[1]
        areas[slug] = area
    return areas


def discover_specs() -> list[SpecInfo]:
    areas = load_project_areas()
    specs: list[SpecInfo] = []

    for directory in sorted(path for path in SPECS_DIR.iterdir() if path.is_dir()):
        spec_file = directory / "spec.md"
        spec_text = read_text(spec_file) if spec_file.exists() else ""
        title = first_match(r"^# Feature Specification:\s*(.+)$", spec_text, directory.name)
        status = first_match(r"^\*\*Status\*\*:\s*(.+)$", spec_text, "n/d")
        files = sorted(
            path
            for path in directory.rglob("*")
            if path.is_file() and not path.name.startswith(".")
        )
        specs.append(
            SpecInfo(
                directory=directory,
                slug=directory.name,
                title=title,
                status=status,
                area=areas.get(directory.name, "Area non censita nel project map"),
                files=files,
                checklist_done=checkbox_counts(directory / "checklists" / "requirements.md"),
                tasks_done=checkbox_counts(directory / "tasks.md"),
            )
        )

    return specs


def active_feature_slug() -> str:
    if not FEATURE_JSON.exists():
        return ""
    try:
        data = json.loads(read_text(FEATURE_JSON))
    except json.JSONDecodeError:
        return ""
    feature_dir = data.get("feature_directory", "")
    return Path(feature_dir).name if feature_dir else ""


def generated_rel_from_docs(path: Path) -> str:
    return path.relative_to(DOCS_DIR).as_posix()


def generated_rel_from_spec_index(path: Path) -> str:
    return path.relative_to(OUT_DIR).as_posix()


def mirror_markdown_files(specs: list[SpecInfo]) -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    for spec in specs:
        for source in spec.files:
            relative = source.relative_to(ROOT)
            target = OUT_DIR / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    if CONSTITUTION.exists():
        target = OUT_DIR / "governance" / "constitution.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CONSTITUTION, target)

    source_dir = OUT_DIR / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    if README.exists():
        shutil.copy2(README, source_dir / "README.md")
    if PROPOSAL.exists():
        shutil.copy2(PROPOSAL, source_dir / "PROPOSTA-servizio-gestione-modelli-bando.md")


def artifact_links(spec: SpecInfo) -> str:
    links: list[str] = []
    for relative_name, label in KNOWN_ARTIFACTS:
        source = spec.directory / relative_name
        if not source.exists():
            continue
        mirrored = OUT_DIR / source.relative_to(ROOT)
        links.append(f"[{label}]({generated_rel_from_spec_index(mirrored)})")
    return " · ".join(links) if links else "Nessun artefatto markdown"


def progress(done_total: tuple[int, int]) -> str:
    done, total = done_total
    if total == 0:
        return "-"
    return f"{done}/{total}"


def openapi_files(spec: SpecInfo) -> list[Path]:
    return [
        path
        for path in spec.files
        if path.suffix in {".yaml", ".yml", ".json"} and "openapi" in path.name.lower()
    ]


def write_active_feature(specs: list[SpecInfo]) -> None:
    active_slug = active_feature_slug()
    active = next((spec for spec in specs if spec.slug == active_slug), None)

    lines = [
        "# Feature Attiva",
        "",
        "_Pagina generata automaticamente da `scripts/generate-spec-docs.py`._",
        "",
    ]

    if active is None:
        lines.extend(
            [
                "Nessuna feature attiva rilevata in `.specify/feature.json`.",
                "",
            ]
        )
    else:
        artifact_lines = [
            f"- [{label}](specs/{active.slug}/{relative_name})"
            for relative_name, label in KNOWN_ARTIFACTS
            if (active.directory / relative_name).exists()
        ]
        lines.extend(
            [
                f"Feature attiva: **{active.slug}**",
                "",
                f"Area: {active.area}",
                "",
                f"Stato checklist: **{progress(active.checklist_done)}**",
                "",
                f"Stato tasks: **{progress(active.tasks_done)}**",
                "",
                "## Artefatti Principali",
                "",
                *(artifact_lines or ["- Nessun artefatto principale trovato"]),
                "",
                "## Blocco Di Partenza",
                "",
                f"Per la feature `{active.slug}` lo sviluppo parte dalle task di setup e fondazione",
                "descritte nel relativo `tasks.md`:",
                "",
                f"- [Tasks](specs/{active.slug}/tasks.md)",
                "",
                "Completare prima le fasi condivise/foundational, poi procedere con le user",
                "story in ordine di priorita'.",
            ]
        )

    (OUT_DIR / "active-feature.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_api_readiness(specs: list[SpecInfo]) -> None:
    lines = [
        "# API Readiness",
        "",
        "_Pagina generata automaticamente da `scripts/generate-spec-docs.py`._",
        "",
        "Questa pagina mostra se le API sono coperte da contratti leggibili prima",
        "dell'implementazione runtime.",
        "",
        "## Regola",
        "",
        "- Ogni API pubblica o di integrazione deve avere OpenAPI versionato.",
        "- Swagger UI e ReDoc, o equivalenti, devono derivare dalla stessa sorgente OpenAPI.",
        "- Ogni flusso rilevante deve avere esempi JSON pubblicabili di successo ed errore.",
        "- Esempi e documentazione non devono contenere token, secret, dati reali o URL",
        "  ambientali sensibili.",
        "",
        "## Copertura Attuale",
        "",
        "| Spec | Area | OpenAPI versionato | Note |",
        "|---|---|---|---|",
    ]

    for spec in specs:
        files = openapi_files(spec)
        if files:
            links = " · ".join(
                f"[{path.name}]({generated_rel_from_spec_index(OUT_DIR / path.relative_to(ROOT))})"
                for path in files
            )
            note = "Contratto presente"
        else:
            links = "-"
            if spec.slug.startswith(("004-", "005-")):
                note = "Da completare prima di implementare generazione, stato o download"
            elif spec.slug.startswith(("006-", "007-")):
                note = "Da definire quando la spec produce API operative"
            else:
                note = "Nessun OpenAPI rilevato"
        lines.append(f"| {spec.slug} | {spec.area} | {links} | {note} |")

    lines.extend(
        [
            "",
            "## API Da Coprire Prima Dello Sviluppo Runtime",
            "",
            "- `POST /documenti/genera`: richiesta generazione bozza/ufficiale, idempotenza,",
            "  output italiano/inglese quando previsto, errori validazione/autorizzazione/rendering.",
            "- `GET /documenti/generazioni/{id}/stato`: stato pubblico, riferimento, errori",
            "  funzionali e autorizzazione.",
            "- `GET /documenti/generazioni/{id}/download` o riferimento equivalente:",
            "  recupero file secondo stato e autorizzazione.",
            "",
            "Questi endpoint appartengono alle spec `004-generazione-documenti-pdf` e",
            "`005-storage-idempotenza-consultazione`, che devono completare plan/tasks/OpenAPI",
            "prima dell'implementazione.",
        ]
    )

    (OUT_DIR / "api-readiness.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_roadmap(specs: list[SpecInfo]) -> None:
    lines = [
        "# Roadmap Spec Kit",
        "",
        "_Pagina generata automaticamente da `scripts/generate-spec-docs.py`._",
        "",
        "## Lettura Per Blocchi",
        "",
        "1. Catalogo e contratto dati: `001`.",
        "2. Dominio configurabile e builder backend: `002` e `003`.",
        "3. Sicurezza, autorizzazioni e audit: `006`.",
        "4. Generazione PDF, stato, download e idempotenza: `004` e `005`.",
        "5. Frontend builder e consultazione: `007`.",
        "6. Fondamenta, mock, test, documentazione API e readiness PA: `009`.",
        "7. Predisposizione AI/MCP: `008`.",
        "",
        "## Stato Artefatti",
        "",
        "| Spec | Plan | Tasks | Checklist |",
        "|---|---:|---:|---:|",
    ]

    for spec in specs:
        plan = "si" if (spec.directory / "plan.md").exists() else "no"
        tasks = progress(spec.tasks_done)
        checklist = progress(spec.checklist_done)
        lines.append(f"| {spec.slug} | {plan} | {tasks} | {checklist} |")

    lines.extend(
        [
            "",
            "## Blocco Prima Di API + PDF",
            "",
            "- Completare `009` almeno fino a `T025` per fondamenta e readiness.",
            "- Completare Spec Kit operativo di `004/005`: plan, data model, OpenAPI, quickstart",
            "  e tasks per generazione, stato, download e idempotenza.",
            "- Solo dopo implementare gli endpoint runtime e il renderer PDF minimo.",
        ]
    )

    (OUT_DIR / "roadmap.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_decisions_and_vincoli() -> None:
    lines = [
        "# Decisioni E Vincoli",
        "",
        "_Pagina generata automaticamente da `scripts/generate-spec-docs.py`._",
        "",
        "## Vincoli Non Negoziabili",
        "",
        "- GEMODO non legge ne' scrive il database GEBAN.",
        "- Le integrazioni passano da contratti espliciti.",
        "- I documenti operativi usano solo versioni modello pubblicate.",
        "- Generazione, stato, download e fallimenti devono essere tracciabili e auditabili.",
        "- Keycloak gestisce identita', client, audience e ruoli/claim generali.",
        "- GEMODO gestisce autorizzazioni fini su profili, modelli, contratti e operazioni.",
        "- I ruoli applicativi GEMODO sono client roles sul client `gemodo-backend` (realm Keycloak condiviso `cnr`), mai realm roles.",
        "- Il builder visuale futuro non consente HTML/CSS/script liberi inseriti dall'utente.",
        "- Le API devono avere OpenAPI, esempi e documentazione interattiva prima dello sviluppo runtime.",
        "- La documentazione pubblicabile non deve contenere segreti, token o dati reali.",
        "",
        "## Decisioni Gia' Chiarite In `009`",
        "",
        "- Bando multiplo: PDF unico sul bando padre con dati rilevanti dei figli.",
        "- Ribando: nuovo bando, nuovo documento, nuovi riferimenti e tracciabilita' del precedente.",
        "- Bando inglese: modello/output integrale tradotto quando richiesto.",
        "- Client proposti: `gemodo-frontend`, `gemodo-backend`, `geban-backend`.",
        "- Profili integrazione: autorizzazioni fini dentro GEMODO, non in Keycloak.",
        "- Modello documento: struttura controllata e versionata, non HTML libero.",
        "- Autenticazione GEBAN -> GEMODO (`SEC-006-001`, risolta 2026-07-29): token tecnico Keycloak (client credentials) del client `geban-backend` con ruolo `DOCUMENTI_GENERATORE`; utente reale e contesto bando nel payload solo per audit, mai nel token. Token exchange resta evoluzione futura non richiesta.",
        "- Approvazione modello (`SEC-006-002`, risolta 2026-07-29): nessuna separazione gestore/revisore/approvatore nella prima release; la pubblicazione fatta da `GEMODO_MODELLI_GESTORE` vale come approvazione. Ruoli revisore/approvatore restano riservati e inattivi per un'eventuale attivazione futura.",
        "",
        "## Decisioni Da Confermare Prima Delle Parti Impattate",
        "",
        "- Configurazione Keycloak di produzione: da richiedere al referente infrastruttura Keycloak CNR dopo validazione in ambiente di test (`sso.test.si.cnr.it`, realm `cnr`).",
        "- Storage definitivo o riferimento documentale esterno (indipendente dalla decisione SOL: GEMODO necessita comunque di uno storage/copia di lavoro propria).",
        "- Confine con stampa, pubblicazione SOL e moduli downstream.",
        "- Licenza open source definitiva prima della pubblicazione pubblica.",
        "",
        "## Link Utili",
        "",
        "- [Costituzione](governance/constitution.md)",
        "- [Project map](../project-map.md)",
        "- [Feature attiva](active-feature.md)",
        "- [API readiness](api-readiness.md)",
    ]

    (OUT_DIR / "decisions-and-vincoli.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index(specs: list[SpecInfo]) -> None:
    lines: list[str] = [
        "# Spec Kit Index",
        "",
        "_Pagina generata automaticamente da `scripts/generate-spec-docs.py`._",
        "",
        "## Documento Sorgente",
        "",
        "La proposta e' il documento condivisibile con i colleghi e la base da cui derivano",
        "le specifiche Spec Kit.",
        "",
    ]

    if PROPOSAL.exists():
        lines.append("- [PROPOSTA - Servizio Gestione Modelli Bando](source/PROPOSTA-servizio-gestione-modelli-bando.md)")
        lines.append("")

    lines.extend(
        [
        "## Vista Sintetica",
        "",
        "| Spec | Area | Stato | Checklist | Tasks | Artefatti |",
        "|---|---|---|---:|---:|---|",
        ]
    )

    for spec in specs:
        spec_link = OUT_DIR / "specs" / spec.slug / "spec.md"
        lines.append(
            "| "
            f"[{spec.slug}]({generated_rel_from_spec_index(spec_link)})"
            f" | {spec.area}"
            f" | {spec.status}"
            f" | {progress(spec.checklist_done)}"
            f" | {progress(spec.tasks_done)}"
            f" | {artifact_links(spec)}"
            " |"
        )

    lines.extend(
        [
            "",
            "## Struttura Generata",
            "",
            "I file sotto `docs/spec-kit/specs/` sono copie generate dagli artefatti in `specs/`.",
            "Non modificarli a mano: rigenera la documentazione dopo ogni modifica Spec Kit.",
            "",
            "```bash",
            "python3 scripts/generate-spec-docs.py",
            "mkdocs serve",
            "```",
            "",
            "## Pagine Di Sintesi",
            "",
            "- [Feature attiva](active-feature.md)",
            "- [Roadmap Spec Kit](roadmap.md)",
            "- [API readiness](api-readiness.md)",
            "- [Decisioni e vincoli](decisions-and-vincoli.md)",
            "",
            "## Governance",
            "",
        ]
    )

    if CONSTITUTION.exists():
        lines.append("- [Costituzione del progetto](governance/constitution.md)")
    lines.append("- [Project map](../project-map.md)")
    if README.exists():
        lines.append("- [README](source/README.md)")
    if PROPOSAL.exists():
        lines.append("- [Proposta sorgente](source/PROPOSTA-servizio-gestione-modelli-bando.md)")

    (OUT_DIR / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_docs_home(specs: list[SpecInfo]) -> None:
    planned = sum(1 for spec in specs if (spec.directory / "plan.md").exists())
    tasked = sum(1 for spec in specs if (spec.directory / "tasks.md").exists())

    lines = [
        "# GEMODO CNR - Documentazione",
        "",
        "Questa documentazione pubblica gli artefatti Spec Kit in forma navigabile.",
        "",
        "## Documento Da Condividere",
        "",
        "La proposta e' il documento principale da condividere con i colleghi. Le specifiche",
        "sono il lavoro di dettaglio derivato da quel documento.",
        "",
    ]

    if PROPOSAL.exists():
        lines.extend(
            [
                "- [Apri la proposta](spec-kit/source/PROPOSTA-servizio-gestione-modelli-bando.md)",
                "",
            ]
        )

    lines.extend(
        [
        "## Entrate Principali",
        "",
        "- [Proposta sorgente](spec-kit/source/PROPOSTA-servizio-gestione-modelli-bando.md)",
        "- [Spec Kit Index](spec-kit/index.md)",
        "- [Feature attiva](spec-kit/active-feature.md)",
        "- [Roadmap Spec Kit](spec-kit/roadmap.md)",
        "- [API readiness](spec-kit/api-readiness.md)",
        "- [Decisioni e vincoli](spec-kit/decisions-and-vincoli.md)",
        "- [Readiness open source/PA](open-source-pa-readiness.md)",
        "- [Project Map](project-map.md)",
        "",
        "## Stato Generato",
        "",
        f"- Specifiche rilevate: **{len(specs)}**",
        f"- Specifiche con `plan.md`: **{planned}**",
        f"- Specifiche con `tasks.md`: **{tasked}**",
        "",
        "## Aggiornamento",
        "",
        "L'indice viene rigenerato leggendo `specs/`. Per aggiornare localmente:",
        "",
        "```bash",
        "python3 scripts/generate-spec-docs.py",
        "mkdocs serve",
        "```",
        ]
    )
    (DOCS_DIR / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    specs = discover_specs()
    mirror_markdown_files(specs)
    write_active_feature(specs)
    write_api_readiness(specs)
    write_roadmap(specs)
    write_decisions_and_vincoli()
    write_index(specs)
    write_docs_home(specs)


if __name__ == "__main__":
    main()
