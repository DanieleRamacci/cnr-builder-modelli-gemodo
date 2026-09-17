"""Fetch an approved discovery URL; validate the tree before caching it."""

from __future__ import annotations

import json
from time import monotonic
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from pydantic import ValidationError

from app.common.errors import ErrorCode

from app.discovery.cache import CacheDiscovery
from app.discovery.errors import DiscoveryError, risposta_non_valida
from app.discovery.schemas import CatalogoDiscovery


def _origin(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL discovery non valido")
    if parsed.fragment:
        raise ValueError("L'URL discovery non puo' contenere un frammento")
    return parsed.scheme, parsed.hostname.lower(), parsed.port or (443 if parsed.scheme == "https" else 80)


def _reject_constant(value: str) -> None:
    raise ValueError("Costante JSON non valida")


class AdapterHTTP:
    def __init__(
        self, url: str, *, cache: CacheDiscovery | None = None,
        client: httpx.Client | None = None, timeout_seconds: float = 10,
        max_response_bytes: int = 2 * 1024 * 1024, max_pages: int = 64,
        max_depth: int = 64,
    ) -> None:
        self.origin = _origin(url)
        if timeout_seconds <= 0 or max_response_bytes < 1 or max_pages < 1 or max_depth < 1:
            raise ValueError("I limiti discovery devono essere positivi")
        self.url = url
        self.cache = cache if cache is not None else CacheDiscovery()
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.max_pages = max_pages
        self.max_depth = max_depth

    def catalogo_discovery(
        self, codice_tipo_documento: str, forza_aggiornamento: bool = False
    ) -> CatalogoDiscovery:
        return self.cache.get_or_load(
            (self.url, codice_tipo_documento),
            lambda: self._fetch(codice_tipo_documento), force=forza_aggiornamento,
        )

    def _fetch(self, codice: str) -> CatalogoDiscovery:
        if self.client is not None:
            return self._fetch_with_client(self.client, codice)
        with httpx.Client() as client:
            return self._fetch_with_client(client, codice)

    def _fetch_with_client(self, client: httpx.Client, codice: str) -> CatalogoDiscovery:
        url: str | None = self.url
        seen: set[str] = set()
        raccolta: dict[str, Any] | None = None
        deadline = monotonic() + self.timeout_seconds
        total_bytes = 0
        try:
            while url is not None:
                if url in seen or len(seen) >= self.max_pages or _origin(url) != self.origin:
                    raise risposta_non_valida()
                seen.add(url)
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise httpx.TimeoutException("Discovery deadline")
                with client.stream("GET", url, timeout=remaining, follow_redirects=False) as response:
                    if response.status_code != 200:
                        raise DiscoveryError(
                            ErrorCode.DISCOVERY_NON_DISPONIBILE, "Il servizio discovery non e' disponibile",
                            status_code=503,
                        )
                    if response.headers.get("content-type", "").split(";")[0].strip() != "application/json":
                        raise risposta_non_valida()
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > self.max_response_bytes:
                            raise risposta_non_valida()
                        if monotonic() > deadline:
                            raise httpx.TimeoutException("Discovery deadline")
                        raw.extend(chunk)
                page = json.loads(raw, parse_constant=_reject_constant)
                fragments, next_href = self._page(page)
                for fragment in fragments:
                    if not isinstance(fragment, dict) or codice not in fragment:
                        raise risposta_non_valida()
                    struttura = fragment[codice]
                    if not isinstance(struttura, dict) or not isinstance(struttura.get("nodi"), list):
                        raise risposta_non_valida()
                    if raccolta is None:
                        raccolta = dict(struttura)
                        raccolta["nodi"] = list(struttura["nodi"])
                    else:
                        if raccolta.get("validita") != struttura.get("validita"):
                            raise risposta_non_valida()
                        raccolta["nodi"].extend(struttura["nodi"])
                url = urljoin(url, next_href) if next_href is not None else None
            if raccolta is None:
                raise risposta_non_valida()
            self._check_depth(raccolta["nodi"])
            return CatalogoDiscovery.model_validate({**raccolta, "codice_tipo_documento": codice})
        except httpx.RequestError:
            raise DiscoveryError(
                ErrorCode.DISCOVERY_NON_DISPONIBILE, "Impossibile contattare il servizio discovery",
                status_code=503,
            ) from None
        except (ValueError, TypeError, KeyError, RecursionError, ValidationError):
            raise risposta_non_valida() from None

    @staticmethod
    def _page(page: Any) -> tuple[list[dict], str | None]:
        if not isinstance(page, dict):
            raise risposta_non_valida()
        if "_embedded" not in page:
            return [page], None
        embedded = page["_embedded"]
        if not isinstance(embedded, dict) or not isinstance(embedded.get("discovery"), list):
            raise risposta_non_valida()
        links = page.get("_links", {})
        if not isinstance(links, dict):
            raise risposta_non_valida()
        next_link = links.get("next")
        if next_link is None:
            return embedded["discovery"], None
        if not isinstance(next_link, dict) or not isinstance(next_link.get("href"), str) or not next_link["href"]:
            raise risposta_non_valida()
        return embedded["discovery"], next_link["href"]

    def _check_depth(self, nodi: list) -> None:
        stack = [(nodo, 1) for nodo in nodi]
        while stack:
            nodo, depth = stack.pop()
            if depth > self.max_depth or not isinstance(nodo, dict):
                raise risposta_non_valida()
            figli = nodo.get("figli", [])
            if not isinstance(figli, list):
                raise risposta_non_valida()
            stack.extend((figlio, depth + 1) for figlio in figli)
