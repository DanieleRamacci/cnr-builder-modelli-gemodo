from copy import deepcopy

import httpx
import pytest

from app.discovery.adapter_http import AdapterHTTP
from app.discovery.errors import DiscoveryError


def fragment(code="TD", validita="2026-09-17T00:00:00Z"):
    return {"BANDO_CONCORSO": {"validita": validita, "nodi": [{
        "codice": code, "descrizione": code,
        "lingue_possibili": ["IT", "EN"],
        "campi": [{"codice": "titolo_it", "etichetta": "Titolo", "tipo": "string",
                   "lingua": "IT", "ordine": 1, "obbligatorio": True}],
    }]}}


def page(fragment, next_href=None):
    result = {"_embedded": {"discovery": [fragment]}}
    if next_href is not None:
        result["_links"] = {"next": {"href": next_href}}
    return result


def test_real_http_single_response_and_cache(discovery_server):
    base, responses, requests = discovery_server
    responses["/discovery"] = (200, fragment())
    adapter = AdapterHTTP(base + "/discovery")
    assert adapter.catalogo_discovery("BANDO_CONCORSO").nodi[0].codice == "TD"
    adapter.catalogo_discovery("BANDO_CONCORSO")
    assert requests == ["/discovery"]


def test_real_http_hal_assembles_pages(discovery_server):
    base, responses, requests = discovery_server
    responses["/discovery?page=0"] = (200, page(fragment("TD"), "?page=1"))
    responses["/discovery?page=1"] = (200, page(fragment("CP")))
    catalogo = AdapterHTTP(base + "/discovery?page=0").catalogo_discovery("BANDO_CONCORSO")
    assert [n.codice for n in catalogo.nodi] == ["TD", "CP"]
    assert requests == ["/discovery?page=0", "/discovery?page=1"]


@pytest.mark.parametrize("kind", [
    "other_origin", "downgrade", "credentials", "cycle", "page_limit",
    "version_change", "duplicate_branch", "bad_link", "bad_envelope", "bad_second_page",
])
def test_pagination_rejects_invalid_or_unsafe_pages(kind):
    first = page(fragment("TD"), "?page=1")
    second = page(fragment("CP"))
    if kind == "other_origin":
        first["_links"]["next"]["href"] = "https://other.example/discovery"
    elif kind == "downgrade":
        first["_links"]["next"]["href"] = "http://geban.example/discovery"
    elif kind == "credentials":
        first["_links"]["next"]["href"] = "https://user:secret@geban.example/discovery"
    elif kind == "cycle":
        second["_links"] = {"next": {"href": "?page=0"}}
    elif kind == "version_change":
        second = page(fragment("CP", "2026-09-18T00:00:00Z"))
    elif kind == "duplicate_branch":
        second = deepcopy(first)
        second.pop("_links")
    elif kind == "bad_link":
        first["_links"]["next"] = "?page=1"
    elif kind == "bad_envelope":
        first["_embedded"]["discovery"] = {}
    elif kind == "bad_second_page":
        second = {"BANDO_CONCORSO": {"validita": "invalid", "nodi": "not an array"}}
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=first if len(calls) == 1 else second)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = AdapterHTTP("https://geban.example/discovery?page=0", client=client,
                          max_pages=1 if kind == "page_limit" else 64)
    with pytest.raises(DiscoveryError) as exc:
        adapter.catalogo_discovery("BANDO_CONCORSO")
    assert exc.value.codice == "DISCOVERY_NON_CONFORME"
    if kind in {"other_origin", "downgrade", "credentials", "bad_link", "bad_envelope", "page_limit"}:
        assert len(calls) == 1
