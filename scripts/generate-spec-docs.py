#!/usr/bin/env python3
"""Generate MkDocs pages from Spec Kit artifacts."""

from __future__ import annotations

import re
import shutil
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

KNOWN_ARTIFACTS = [
    ("spec.md", "Spec"),
    ("checklists/requirements.md", "Checklist"),
    ("plan.md", "Plan"),
    ("tasks.md", "Tasks"),
    ("data-model.md", "Data model"),
    ("research.md", "Research"),
    ("quickstart.md", "Quickstart"),
    ("keycloak-jwt.md", "Keycloak JWT"),
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


def write_index(specs: list[SpecInfo]) -> None:
    lines: list[str] = [
        "# Spec Kit Index",
        "",
        "_Pagina generata automaticamente da `scripts/generate-spec-docs.py`._",
        "",
        "## Vista Sintetica",
        "",
        "| Spec | Area | Stato | Checklist | Tasks | Artefatti |",
        "|---|---|---|---:|---:|---|",
    ]

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
        "## Entrate Principali",
        "",
        "- [Spec Kit Index](spec-kit/index.md)",
        "- [Project Map](project-map.md)",
        "- [Proposta sorgente](spec-kit/source/PROPOSTA-servizio-gestione-modelli-bando.md)",
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
    (DOCS_DIR / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    specs = discover_specs()
    mirror_markdown_files(specs)
    write_index(specs)
    write_docs_home(specs)


if __name__ == "__main__":
    main()
