import glob
import os
import re

from . import meta
from ..classify import snap_kind
from .base import Backend, Package, have, run

SYSTEM_RE = re.compile(r"^(core\d*|snapd|bare|gnome-.*|gtk-common-themes|mesa-.*|"
                       r"kf\d+-.*|snapd-desktop-integration)$")


def is_system(name):
    return bool(SYSTEM_RE.match(name))


def parse_list(text):
    """Вывод `snap list`: Name Version Rev Tracking Publisher Notes."""
    lines = text.splitlines()
    res = []
    for line in lines[1:]:
        cols = line.split()
        if len(cols) < 3:
            continue
        notes = cols[-1] if len(cols) >= 6 else ""
        res.append({"name": cols[0], "version": cols[1], "rev": cols[2], "notes": notes})
    return res


def parse_info_summary(text):
    m = re.search(r"^summary:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def snap_size(name, rev):
    """Размер .snap-файла в /var/lib/snapd/snaps (быстро и без root)."""
    p = f"/var/lib/snapd/snaps/{name}_{rev}.snap"
    try:
        return os.path.getsize(p)
    except OSError:
        return 0


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def collect_one(name, rev, langs, root="/snap", snaps="/var/lib/snapd/snaps",
                exported="/var/lib/snapd/desktop/applications"):
    cur = os.path.join(root, name, "current")
    entries = []
    for pat in (os.path.join(exported, name + "_*.desktop"), os.path.join(cur, "meta/gui/*.desktop")):
        for path in sorted(glob.glob(pat)):
            entries.append(meta.parse_desktop(_read(path), langs))
        if entries:
            break
    best = meta.pick_desktop(entries)
    yaml = meta.parse_snap_yaml(_read(os.path.join(cur, "meta/snap.yaml")))
    info = {}
    if best:
        info["display_name"] = best["name"]
        icon = meta.resolve_icon(best["icon"], cur)
        if icon.startswith("/") and not os.path.exists(icon):
            icon = ""
        info["icon"] = icon
    elif yaml.get("title"):
        info["display_name"] = yaml["title"]
    info["description"] = (meta.desktop_summary(best) if best else "") or yaml.get("summary", "")
    for cand in (os.path.join(snaps, f"{name}_{rev}.snap"), os.path.join(root, name)):
        try:
            info["installed"] = os.stat(cand).st_mtime
            break
        except OSError:
            continue
    return info


class SnapBackend(Backend):
    source = "snap"

    def available(self):
        return have("snap")

    def list(self):
        _, out = run(["snap", "list"])
        pkgs = []
        for e in parse_list(out):
            system = is_system(e["name"]) or "base" in e["notes"]
            pkgs.append(Package(name=e["name"], source="snap", version=e["version"],
                                size=snap_size(e["name"], e["rev"]),
                                description="", manual=not system, kind=snap_kind(system),
                                protected=e["name"] in ("snapd", "core", "bare") or e["name"].startswith("core"),
                                extra={"rev": e["rev"]}))
        return pkgs

    def collect(self, pkgs):
        langs = meta.user_langs()
        res = {}
        for p in pkgs:
            res[p.name] = collect_one(p.name, p.extra.get("rev", ""), langs)
        return res

    def remove_cmd(self, names):
        return [["pkexec", "snap", "remove"] + list(names)]
