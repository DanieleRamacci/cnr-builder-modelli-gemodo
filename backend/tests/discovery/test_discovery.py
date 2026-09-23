from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import ValidationError

from app.discovery.adapter_http import AdapterHTTP
from app.discovery.cache import CacheDiscovery
from app.discovery.errors import DiscoveryError
from app.discovery.schemas import CatalogoDiscovery


URL = "https://geban.example/api/discovery"


@pytest.fixture
def payload():
    return {
        "BANDO_CONCORSO": {
            "validita": "2026-09-17T00:00:00Z",
            "nodi": [{
                "codice": "TD", "descrizione": "Tempo Determinato",
                "figli": [{
                    "codice": "RICERCATORE", "descrizione": "Ricercatore",
                    "livelli_possibili": ["I", "II", "III"], "livelloBase": "III",
                    "lingue_possibili": ["IT", "EN"],
                    "campi": [{
                        "codice": "titolo_it", "etichetta": "Titolo", "tipo": "string",
                        "lingua": "IT", "obbligatorio": True, "ordine": 1,
                        "validazione": {"minLength": 1},
                    }],
                }],
            }],
        },
    }


def adapter_for(payload, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)))
    return AdapterHTTP(URL, client=client, **kwargs)


def test_recursive_paths_and_alias_at_three_levels(payload):
    parent = payload["BANDO_CONCORSO"]["nodi"][0]
    parent["figli"] = [{"codice": "AREA", "descrizione": "Area", "figli": parent["figli"]}]
    catalogo = adapter_for(payload).catalogo_discovery("BANDO_CONCORSO")
    nodo = catalogo.indice_percorsi()[("TD", "AREA", "RICERCATORE")]
    assert nodo.livello_base == "III"
    assert nodo.lingue_possibili == ("IT", "EN")
    assert "livelloBase" not in nodo.model_dump()
    assert nodo.campi[0].validazione == {"minLength": 1}


def test_geban_languages_alias_is_normalized(payload):
    leaf = payload["BANDO_CONCORSO"]["nodi"][0]["figli"][0]
    leaf["lingue"] = ["IT", "ENG"]
    leaf.pop("lingue_possibili")

    nodo = adapter_for(payload).catalogo_discovery("BANDO_CONCORSO").nodi[0].figli[0]

    assert nodo.lingue_possibili == ("IT", "EN")
    assert "lingue" not in nodo.model_dump()


def test_geban_languages_alias_must_match_canonical_value(payload):
    leaf = payload["BANDO_CONCORSO"]["nodi"][0]["figli"][0]
    leaf["lingue"] = ["IT"]

    with pytest.raises(DiscoveryError) as exc:
        adapter_for(payload).catalogo_discovery("BANDO_CONCORSO")

    assert exc.value.codice == "DISCOVERY_NON_CONFORME"


def test_codes_may_repeat_in_different_branches(payload):
    copy = deepcopy(payload["BANDO_CONCORSO"]["nodi"][0])
    copy["codice"] = "CP"
    payload["BANDO_CONCORSO"]["nodi"].append(copy)
    indice = adapter_for(payload).catalogo_discovery("BANDO_CONCORSO").indice_percorsi()
    assert ("CP", "RICERCATORE") in indice and ("TD", "RICERCATORE") in indice


@pytest.mark.parametrize("change", [
    "both", "neither", "duplicate_roots", "duplicate_children", "duplicate_fields",
    "default_conflict", "unknown_default", "string_bool", "string_order",
    "missing_field", "invalid_type", "invalid_date", "epoch_date",
    "duplicate_languages", "duplicate_levels", "metadata_on_branch",
])
def test_invalid_structure_is_functional_error(payload, change):
    root = payload["BANDO_CONCORSO"]["nodi"][0]
    leaf = root["figli"][0]
    field = leaf["campi"][0]
    if change == "both":
        leaf["figli"] = []
    elif change == "neither":
        leaf.pop("campi")
    elif change == "duplicate_roots":
        payload["BANDO_CONCORSO"]["nodi"].append(deepcopy(root))
    elif change == "duplicate_children":
        root["figli"].append(deepcopy(leaf))
    elif change == "duplicate_fields":
        leaf["campi"].append(deepcopy(field))
    elif change == "default_conflict":
        leaf["livello_base"] = "II"
    elif change == "unknown_default":
        leaf["livelloBase"] = "VII"
    elif change == "string_bool":
        field["obbligatorio"] = "true"
    elif change == "string_order":
        field["ordine"] = "1"
    elif change == "missing_field":
        field.pop("lingua")
    elif change == "invalid_type":
        field["tipo"] = "enum"
    elif change == "invalid_date":
        payload["BANDO_CONCORSO"]["validita"] = "2026-09-17T00:00:00"
    elif change == "epoch_date":
        payload["BANDO_CONCORSO"]["validita"] = 1789600000
    elif change == "duplicate_languages":
        leaf["lingue_possibili"] = ["IT", "IT"]
    elif change == "duplicate_levels":
        leaf["livelli_possibili"] = ["I", "I"]
    elif change == "metadata_on_branch":
        root["lingue_possibili"] = ["IT"]
    with pytest.raises(DiscoveryError) as exc:
        adapter_for(payload).catalogo_discovery("BANDO_CONCORSO")
    assert exc.value.codice == "DISCOVERY_NON_CONFORME"
    assert exc.value.status_code == 502


def test_una_foglia_senza_lingua_e_conforme(payload):
    """011 FR-005/FR-006: la lingua non e' piu' obbligatoria sulla foglia.

    Era il caso `missing_languages` dell'elenco qui sopra, cioe' una risposta
    **non conforme**: una foglia priva di `lingue_possibili` faceva fallire
    l'intera discovery con `DISCOVERY_NON_CONFORME`. Un tipo documento che non
    distingue i modelli per lingua - il caso portante di 011 - non poteva
    quindi nemmeno entrare nel sistema. Contratto discovery 0.6.0: la chiave
    diventa opzionale, e questo test presidia il verso nuovo della regola.
    """
    payload["BANDO_CONCORSO"]["nodi"][0]["figli"][0].pop("lingue_possibili")

    catalogo = adapter_for(payload).catalogo_discovery("BANDO_CONCORSO")

    foglia = catalogo.nodi[0].figli[0]
    assert foglia.lingue_possibili is None
    assert foglia.campi, "i campi della foglia restano leggibili"


def test_missing_document_type_is_not_an_empty_catalog(payload):
    with pytest.raises(DiscoveryError):
        adapter_for(payload).catalogo_discovery("CONTRATTO")


def test_cache_expiry_force_and_no_stale_fallback(payload):
    clock = [0.0]
    calls = []
    fail = [False]

    def handler(request):
        calls.append(request)
        if fail[0]:
            raise httpx.ConnectError("Unavailable", request=request)
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = AdapterHTTP(URL, client=client, cache=CacheDiscovery(ttl_seconds=10, clock=lambda: clock[0]))
    first = adapter.catalogo_discovery("BANDO_CONCORSO")
    first.nodi[0].figli[0].campi[0].validazione["minLength"] = 999
    assert adapter.catalogo_discovery("BANDO_CONCORSO").nodi[0].figli[0].campi[0].validazione["minLength"] == 1
    assert len(calls) == 1
    adapter.catalogo_discovery("BANDO_CONCORSO", forza_aggiornamento=True)
    assert len(calls) == 2
    clock[0] = 11
    fail[0] = True
    with pytest.raises(DiscoveryError) as exc:
        adapter.catalogo_discovery("BANDO_CONCORSO")
    assert exc.value.codice == "DISCOVERY_NON_DISPONIBILE"


def test_concurrent_navigation_shares_one_fetch(payload):
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: (calls.append(r), httpx.Response(200, json=payload))[1]
    ))
    adapter = AdapterHTTP(URL, client=client)
    with ThreadPoolExecutor(max_workers=8) as pool:
        catalogs = list(pool.map(lambda _: adapter.catalogo_discovery("BANDO_CONCORSO"), range(16)))
    assert len(calls) == 1
    assert all(c.codice_tipo_documento == "BANDO_CONCORSO" for c in catalogs)


def test_cache_bound_and_isolation():
    cache = CacheDiscovery(max_entries=1)
    loads = []

    def load():
        loads.append(1)
        return CatalogoDiscovery(codice_tipo_documento="X", validita=datetime.now(timezone.utc), nodi=[])

    cache.get_or_load((URL, "X"), load)
    cache.get_or_load((URL, "Y"), load)
    cache.get_or_load((URL, "X"), load)
    assert len(loads) == 3


@pytest.mark.parametrize("kind", ["oversized", "depth", "html", "broken_json", "nan", "redirect", "timeout"])
def test_transport_and_resource_limits(payload, kind):
    def handler(request):
        if kind == "html":
            return httpx.Response(200, text="<html></html>")
        if kind == "broken_json":
            return httpx.Response(200, content=b"{", headers={"content-type": "application/json"})
        if kind == "nan":
            return httpx.Response(200, content=b'{"BANDO_CONCORSO": NaN}', headers={"content-type": "application/json"})
        if kind == "redirect":
            return httpx.Response(302, headers={"location": "https://other.example/discovery"})
        if kind == "timeout":
            raise httpx.ReadTimeout("Timed out", request=request)
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    kwargs = {"max_response_bytes": 10} if kind == "oversized" else {"max_depth": 1} if kind == "depth" else {}
    with pytest.raises(DiscoveryError):
        AdapterHTTP(URL, client=client, **kwargs).catalogo_discovery("BANDO_CONCORSO")


def test_unrecognized_attributes_are_preserved(payload):
    payload["BANDO_CONCORSO"]["nodi"][0]["attributo_futuro"] = {"valori": [1, 2]}
    nodo = adapter_for(payload).catalogo_discovery("BANDO_CONCORSO").nodi[0]
    assert nodo.model_dump()["attributo_futuro"] == {"valori": [1, 2]}


def test_null_fields_with_children_is_invalid():
    with pytest.raises(ValidationError):
        CatalogoDiscovery.model_validate({
            "codice_tipo_documento": "X", "validita": "2026-09-17T00:00:00Z",
            "nodi": [{"codice": "X", "descrizione": "X", "figli": [], "campi": None}],
        })
