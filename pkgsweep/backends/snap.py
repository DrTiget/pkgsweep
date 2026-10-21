import os
import re

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
                                description="", manual=not system,
                                protected=e["name"] in ("snapd", "core", "bare") or e["name"].startswith("core"),
                                extra={"rev": e["rev"]}))
        return pkgs

    def remove_cmd(self, names):
        return [["pkexec", "snap", "remove"] + list(names)]
