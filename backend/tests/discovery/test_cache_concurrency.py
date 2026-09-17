from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from app.discovery.cache import CacheDiscovery
from app.discovery.schemas import CatalogoDiscovery


def _catalogo():
    return CatalogoDiscovery.model_validate({
        "codice_tipo_documento": "DOCUMENTO", "validita": "2026-09-17T00:00:00Z", "nodi": []
    })


def test_different_key_does_not_wait_for_slow_load():
    cache = CacheDiscovery()
    started, release = Event(), Event()

    def slow():
        started.set()
        assert release.wait(3)
        return _catalogo()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.get_or_load, ("url", "A"), slow)
        try:
            assert started.wait(1)
            second = pool.submit(cache.get_or_load, ("url", "B"), _catalogo)
            assert second.result(timeout=1) == _catalogo()
        finally:
            release.set()
        assert first.result(timeout=1) == _catalogo()


def test_same_key_navigation_fetches_once():
    cache = CacheDiscovery()
    started, release = Event(), Event()
    calls = []

    def load():
        calls.append(1)
        started.set()
        assert release.wait(3)
        return _catalogo()

    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(cache.get_or_load, ("url", "A"), load)
        try:
            assert started.wait(1)
            others = [pool.submit(cache.get_or_load, ("url", "A"), load) for _ in range(2)]
        finally:
            release.set()
        results = [first.result(timeout=1)] + [f.result(timeout=1) for f in others]
    assert calls == [1]
    assert all(result == _catalogo() for result in results)
    assert results[0] is not results[1]


def test_failed_loader_releases_same_key_waiters():
    cache = CacheDiscovery()
    started, release = Event(), Event()
    calls = []

    def load():
        calls.append(1)
        if len(calls) == 1:
            started.set()
            assert release.wait(3)
            raise ValueError("Errore di caricamento")
        return _catalogo()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.get_or_load, ("url", "A"), load)
        try:
            assert started.wait(1)
            second = pool.submit(cache.get_or_load, ("url", "A"), load)
        finally:
            release.set()
        with pytest.raises(ValueError):
            first.result(timeout=1)
        assert second.result(timeout=1) == _catalogo()
    assert calls == [1, 1]
    assert cache._pending == {}
