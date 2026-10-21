"""Классификация пакетов: app | library | other (чистая логика, без GTK)."""
import re

LIB_SECTIONS = {"libs", "libdevel", "oldlibs", "python", "perl", "ruby", "javascript", "golang",
                "rust", "haskell", "ocaml", "java", "php", "introspection"}
_LIB_NAME = re.compile(
    r"^(?:lib(?!reoffice)|gir1\.2-|python3-|perl-|node-|golang-|librust-)|"
    r"^lib.*-perl$|(?:-dev|-dbg|-dbgsym|-doc|-common|-data)$")


def apt_kind(name, section="", has_app=False):
    """app — есть видимый .desktop; library — по Section/имени; иначе other (CLI, шрифты, драйверы…)."""
    if has_app:
        return "app"
    sec = section.split("/")[-1] if section else ""
    if sec in LIB_SECTIONS or _LIB_NAME.search(name.split(":")[0]):
        return "library"
    return "other"


def snap_kind(system):
    return "library" if system else "app"


def flatpak_kind(runtime):
    return "library" if runtime else "app"


MODES = [("apps", "Программы"), ("apps_utils", "Программы и утилиты"), ("all", "Всё")]


def kind_visible(kind, mode):
    if mode == "all":
        return True
    if mode == "apps_utils":
        return kind != "library"
    return kind == "app"
