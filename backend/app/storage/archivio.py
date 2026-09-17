"""Local filesystem persistence for generated documents (005, MVP FR-019/020 slice).

The stored path is always derived from a server-generated ``riferimento``
(never from caller-supplied input), so there is no path-traversal surface: a
download always resolves the file through ``DocumentoGenerato.percorso_file``
as read back from the database, not by re-deriving a path from the request.
"""

from __future__ import annotations

from pathlib import Path

from app.core.settings import Settings


def _cartella(settings: Settings) -> Path:
    cartella = Path(settings.gemodo_storage_dir)
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def percorso_per(riferimento: str, settings: Settings) -> Path:
    return _cartella(settings) / f"{riferimento}.pdf"


def salva(riferimento: str, contenuto: bytes, settings: Settings) -> Path:
    percorso = percorso_per(riferimento, settings)
    percorso.write_bytes(contenuto)
    return percorso


def leggi(percorso_file: str) -> bytes:
    return Path(percorso_file).read_bytes()


def rimuovi(percorso: Path) -> None:
    percorso.unlink(missing_ok=True)
