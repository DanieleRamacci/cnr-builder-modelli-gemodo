"""Bounded process-local cache; callers never receive its stored mutable objects."""

from collections import OrderedDict
from threading import Event, RLock
from time import monotonic
from typing import Callable

from app.discovery.schemas import CatalogoDiscovery, MappaDiscovery


class CacheDiscovery:
    def __init__(
        self, ttl_seconds: float = 60, max_entries: int = 32,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if ttl_seconds <= 0 or max_entries < 1:
            raise ValueError("TTL e capienza della cache devono essere positivi")
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.clock = clock
        self._entries: OrderedDict[tuple[str, ...], tuple[float, CatalogoDiscovery | MappaDiscovery]] = OrderedDict()
        self._lock = RLock()
        self._pending: dict[tuple[str, ...], Event] = {}

    def get_or_load(
        self, key: tuple[str, ...], load: Callable[[], CatalogoDiscovery | MappaDiscovery],
        force: bool = False,
    ) -> CatalogoDiscovery | MappaDiscovery:
        # Coalesce navigation fills per key, without locking during HTTP I/O.
        while True:
            with self._lock:
                cached = self._entries.get(key)
                if not force and cached is not None and cached[0] > self.clock():
                    self._entries.move_to_end(key)
                    return cached[1].model_copy(deep=True)
                pending = self._pending.get(key)
                if pending is None:
                    pending = Event()
                    self._pending[key] = pending
                    self._entries.pop(key, None)
                    break
            pending.wait()
        try:
            result = load()
            with self._lock:
                self._entries[key] = (self.clock() + self.ttl_seconds, result.model_copy(deep=True))
                while len(self._entries) > self.max_entries:
                    self._entries.popitem(last=False)
            return result.model_copy(deep=True)
        finally:
            with self._lock:
                self._pending.pop(key, None)
                pending.set()
