"""Фоновый сбор метаданных с кэшем по (источник, имя)."""
import threading

_CACHE = {}
_LOCK = threading.Lock()
FIELDS = ("display_name", "description", "icon", "installed", "last_used", "kind")


def apply(pkg, info):
    for k in FIELDS:
        v = info.get(k)
        if v:
            setattr(pkg, k, v)


def enrich(pkgs, backends, on_done=None):
    """Дополняет Package на месте; on_done(backend.source) после каждого источника."""
    for b in backends:
        mine = [p for p in pkgs if p.source == b.source]
        with _LOCK:
            todo = [p for p in mine if (p.source, p.name) not in _CACHE]
        if todo:
            try:
                got = b.collect(todo)
            except Exception as e:  # сбор метаданных не должен ломать список
                print("collect", b.source, e)
                got = {}
            with _LOCK:
                for p in todo:
                    _CACHE[(p.source, p.name)] = got.get(p.name, {})
        for p in mine:
            apply(p, _CACHE.get((p.source, p.name), {}))
        if on_done:
            on_done(b.source)
