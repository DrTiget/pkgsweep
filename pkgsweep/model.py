"""Чистая логика модели списка (без GTK): выбор, итоги, ключи сортировки, формат дат."""
import time


def fmt_size(n):
    if not n:
        return "—"
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or unit == "ГБ":
            return f"{n:.0f} {unit}" if unit == "Б" else f"{n:.1f} {unit}"
        n /= 1024


def fmt_date(ts, unknown="неизвестно"):
    if not ts:
        return unknown
    return time.strftime("%d.%m.%Y", time.localtime(ts))


def set_selected(pkg, value):
    pkg.selected = bool(value)


def selected(pkgs):
    return [p for p in pkgs if p.selected]


def summary(pkgs):
    sel = selected(pkgs)
    return len(sel), sum(p.size for p in sel)


def cmp(a, b):
    return (a > b) - (a < b)


def cmp_date(a, b):
    """Неизвестная дата (None) — самая старая."""
    return cmp(a or 0, b or 0)
