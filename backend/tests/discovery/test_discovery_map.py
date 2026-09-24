from copy import deepcopy
import json

import httpx
import pytest

from app.discovery.adapter_http import AdapterHTTP
from app.discovery.cache import CacheDiscovery
from app.discovery.errors import DiscoveryError
from tests.discovery.test_pagination import fragment, page


def test_one_response_validates_all_types_and_shares_navigation_cache(discovery_server):
    base, responses, requests = discovery_server
    body = fragment()
    body["VERBALE"] = deepcopy(body["BANDO_CONCORSO"])
    responses["/discovery"] = (200, body)
    adapter = AdapterHTTP(base + "/discovery", cache_scope="software:1:revision:1")
    assert set(adapter.mappa_discovery().cataloghi) == {"BANDO_CONCORSO", "VERBALE"}
    assert adapter.catalogo_discovery("VERBALE").codice_tipo_documento == "VERBALE"
    assert adapter.catalogo_discovery("BANDO_CONCORSO").codice_tipo_documento == "BANDO_CONCORSO"
    assert requests == ["/discovery"]


def test_invalid_unselected_type_rejects_entire_response(discovery_server):
    base, responses, requests = discovery_server
    body = fragment()
    body["VERBALE"] = {"validita": "invalid", "nodi": []}
    responses["/discovery"] = (200, body)
    adapter = AdapterHTTP(base + "/discovery")
    for _ in range(2):
        with pytest.raises(DiscoveryError) as error:
            adapter.catalogo_discovery("BANDO_CONCORSO")
        assert error.value.codice == "DISCOVERY_NON_CONFORME"
    assert len(requests) == 2


def test_hal_pages_may_contain_different_document_types(discovery_server):
    base, responses, _ = discovery_server
    responses["/discovery"] = (200, page(fragment(), "?page=1"))
    responses["/discovery?page=1"] = (200, page({"VERBALE": fragment()["BANDO_CONCORSO"]}))
    assert set(AdapterHTTP(base + "/discovery").mappa_discovery().cataloghi) == {"BANDO_CONCORSO", "VERBALE"}


def test_cache_is_isolated_by_source_and_revision():
    cache = CacheDiscovery()
    calls = []

    def adapter(scope):
        client = httpx.Client(transport=httpx.MockTransport(
            lambda r: (calls.append(scope), httpx.Response(200, json=fragment(scope)))[1]
        ))
        return AdapterHTTP("https://software.example.test/discovery", cache=cache, client=client, cache_scope=scope)

    first = adapter("software:1:revision:1")
    result = first.mappa_discovery()
    result.cataloghi.clear()
    assert first.mappa_discovery().cataloghi
    assert adapter("software:1:revision:2").catalogo_discovery("BANDO_CONCORSO").nodi[0].codice.endswith("2")
    assert adapter("software:2:revision:1").catalogo_discovery("BANDO_CONCORSO").nodi[0].codice.startswith("software:2")
    assert len(calls) == 3


def test_empty_map_is_not_connected(discovery_server):
    base, responses, _ = discovery_server
    responses["/discovery"] = (200, {})
    with pytest.raises(DiscoveryError):
        AdapterHTTP(base + "/discovery").mappa_discovery()


def test_duplicate_json_root_keys_cannot_hide_a_type():
    root = json.dumps(fragment())[1:-1]
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content="{" + root + "," + root + "}", headers={"Content-Type": "application/json"})
    ))
    with pytest.raises(DiscoveryError):
        AdapterHTTP("https://software.example.test/discovery", client=client).mappa_discovery()


def test_map_timeout_is_distinct_without_changing_legacy_catalog_errors():
    def timeout(request):
        raise httpx.ReadTimeout("timeout", request=request)

    client = httpx.Client(transport=httpx.MockTransport(timeout))
    adapter = AdapterHTTP("https://software.example.test/discovery", client=client)
    with pytest.raises(DiscoveryError) as error:
        adapter.mappa_discovery()
    assert error.value.codice == "DISCOVERY_TIMEOUT"
    assert error.value.status_code == 504
    with pytest.raises(DiscoveryError) as error:
        adapter.catalogo_discovery("BANDO_CONCORSO")
    assert error.value.codice == "DISCOVERY_NON_DISPONIBILE"
    assert error.value.status_code == 503


def test_non_conformity_names_the_offending_field_and_paths(discovery_server):
    """L'operatore deve poter vedere *quale* parte dell'albero e' difforme."""
    base, responses, _ = discovery_server
    body = fragment()
    for nodo in body["BANDO_CONCORSO"]["nodi"]:
        for campo in _foglie(nodo):
            campo.pop("etichetta", None)
    responses["/discovery"] = (200, body)
    with pytest.raises(DiscoveryError) as error:
        AdapterHTTP(base + "/discovery").mappa_discovery()
    assert error.value.codice == "DISCOVERY_NON_CONFORME"
    assert "etichetta" in error.value.messaggio
    dettagli = error.value.dettagli
    assert dettagli, "la difformita' deve portare i percorsi difformi"
    assert all(d["percorso"].startswith("BANDO_CONCORSO.nodi.") for d in dettagli)
    assert any("etichetta" in d["percorso"] for d in dettagli)


def _foglie(nodo):
    for campo in nodo.get("campi", []):
        yield campo
    for figlio in nodo.get("figli", []):
        yield from _foglie(figlio)
