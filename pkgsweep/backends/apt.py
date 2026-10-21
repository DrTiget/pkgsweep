import os
import re

import glob

from . import meta
from .base import Backend, Package, Simulation, have, run

SEP = "\t"
QUERY_FMT = SEP.join(["${Package}", "${Version}", "${Installed-Size}", "${Priority}",
                      "${Essential}", "${db:Status-Abbrev}", "${binary:Summary}"]) + "\n"

CRITICAL_PATTERNS = [
    r"ubuntu-desktop.*", r"ubuntu-minimal", r"ubuntu-standard", r"gnome-shell",
    r"gdm3", r"systemd", r"network-manager", r"linux-generic.*", r"sudo", r"apt",
    r"dpkg", r"snapd", r"xorg.*", r"xwayland", r"pipewire", r"gnome-session",
    r"nautilus",
]
_CRIT_RE = re.compile(r"^(?:%s)$" % "|".join(CRITICAL_PATTERNS))


def current_kernel():
    try:
        return os.uname().release
    except AttributeError:
        return ""


def is_critical(name, priority="", essential=False, kernel=None):
    kernel = current_kernel() if kernel is None else kernel
    if essential or priority in ("required", "important"):
        return True
    if _CRIT_RE.match(name):
        return True
    if re.match(r"^linux-(image|modules|modules-extra|headers)-", name) and kernel and kernel in name:
        return True
    return False


def parse_query(text, manual, kernel=None):
    """Разбор вывода dpkg-query -W -f=QUERY_FMT."""
    pkgs = []
    for line in text.splitlines():
        parts = line.split(SEP)
        if len(parts) < 7 or not parts[5].startswith("ii"):
            continue
        name, ver, size, prio, ess, _, desc = parts[:7]
        base = name.split(":")[0]
        try:
            size_b = int(size) * 1024
        except ValueError:
            size_b = 0
        crit = is_critical(base, prio, ess == "yes", kernel)
        pkgs.append(Package(name=name, source="apt", version=ver, size=size_b,
                            description=desc, manual=base in manual or name in manual,
                            protected=crit, extra={"priority": prio}))
    return pkgs


def parse_manual(text):
    return {l.strip() for l in text.splitlines() if l.strip()}


_REMV = re.compile(r"^(?:Remv|Purg) (\S+)")


def parse_simulation(text):
    """Строки 'Remv pkg [ver]' из apt-get -s."""
    out = []
    for line in text.splitlines():
        m = _REMV.match(line)
        if m and m.group(1) not in out:  # purge даёт Purg (иногда и Remv)
            out.append(m.group(1))
    return out


def desktop_index(info_dir="/var/lib/dpkg/info"):
    """pkg -> .desktop-файлы (по спискам файлов dpkg) и mtime *.list как запасная дата установки."""
    desktops, mtimes = {}, {}
    pat = re.compile(r"^(/usr/share/applications/[^/\n]+\.desktop)$", re.M)
    for path in glob.glob(os.path.join(info_dir, "*.list")):
        pkg = os.path.basename(path)[:-5].split(":")[0]
        try:
            mtimes[pkg] = os.stat(path).st_mtime
            with open(path, encoding="utf-8", errors="replace") as f:
                found = pat.findall(f.read())
        except OSError:
            continue
        if found:
            desktops.setdefault(pkg, []).extend(found)
    return {"desktops": desktops, "mtimes": mtimes}


class AptBackend(Backend):
    source = "apt"

    def available(self):
        return have("dpkg-query")

    def list(self):
        _, manual = run(["apt-mark", "showmanual"])
        rc, out = run(["dpkg-query", "-W", "-f", QUERY_FMT])
        return parse_query(out, parse_manual(manual))

    def collect(self, pkgs):
        langs = meta.user_langs()
        index = desktop_index()
        log = meta.read_dpkg_logs()
        tr = meta.read_translations(langs) if langs and langs[-1] != "en" else {}
        res = {}
        for p in pkgs:
            base = p.name.split(":")[0]
            info = {}
            entries = []
            for path in index["desktops"].get(base, []):
                try:
                    with open(path, encoding="utf-8", errors="replace") as f:
                        entries.append(meta.parse_desktop(f.read(), langs))
                except OSError:
                    pass
            best = meta.pick_desktop(entries)
            if best:
                info["display_name"] = best["name"]
                info["icon"] = best["icon"]
                prog = meta.exec_program(best["exec"])
                if prog:
                    info["last_used"] = meta.last_used_from_atime(prog)
            info["description"] = (meta.desktop_summary(best) if best else "") or tr.get(base, "")
            info["installed"] = log.get(base) or index["mtimes"].get(base)
            res[p.name] = info
        return res

    def _info(self, names):
        rc, out = run(["dpkg-query", "-W", "-f", QUERY_FMT] + list(names))
        info = {}
        for line in out.splitlines():
            p = line.split(SEP)
            if len(p) >= 7:
                info[p[0]] = (p[3], p[4] == "yes")
        return info

    def simulate_remove(self, names):
        env = dict(os.environ, LC_ALL="C")
        rc, out = run(["apt-get", "-s", "purge"] + list(names), env=env)
        if rc != 0 and not parse_simulation(out):
            return Simulation(removed=list(names), critical=[], error="apt-get -s завершился с ошибкой")
        removed = parse_simulation(out)
        info = self._info(removed)
        crit = [n for n in removed
                if is_critical(n.split(":")[0], *info.get(n, ("", False)))]
        return Simulation(removed=removed, critical=crit)

    def remove_cmd(self, names):
        return [["pkexec", "apt-get", "-y", "purge"] + list(names)]

    def autoremove_cmd(self):
        return [["pkexec", "apt-get", "-y", "autoremove", "--purge"]]
