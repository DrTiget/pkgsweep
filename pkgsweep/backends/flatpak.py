from .base import Backend, Package, have, run

COLUMNS = "application,name,version,size,installation"


def parse_size(s):
    """'1.2 GB' / '350,5 MB' / '12 bytes' -> байты."""
    s = s.strip().replace(" ", " ").replace(",", ".")
    if not s:
        return 0
    parts = s.split()
    try:
        val = float(parts[0])
    except ValueError:
        return 0
    unit = parts[1].lower() if len(parts) > 1 else "b"
    mult = {"b": 1, "bytes": 1, "byte": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4,
            "kib": 1024, "mib": 1024**2, "gib": 1024**3}.get(unit, 1)
    return int(val * mult)


def parse_list(text, runtime):
    pkgs = []
    for line in text.splitlines():
        c = line.split("\t")
        if len(c) < 5 or not c[0].strip():
            continue
        app, name, ver, size, inst = [x.strip() for x in c[:5]]
        pkgs.append(Package(name=app, display_name=name, source="flatpak", version=ver,
                            size=parse_size(size), description=name if name != app else "",
                            manual=not runtime, extra={"installation": inst, "runtime": runtime}))
    return pkgs


class FlatpakBackend(Backend):
    source = "flatpak"

    def available(self):
        return have("flatpak")

    def list(self):
        pkgs = []
        for rt in (False, True):
            cmd = ["flatpak", "list", "--columns=" + COLUMNS, "--app" if not rt else "--runtime"]
            _, out = run(cmd)
            pkgs += parse_list(out, rt)
        return pkgs

    def remove_cmd(self, names, installs=None):
        """installs: {app: 'system'|'user'}; system-установки — через pkexec."""
        installs = installs or {}
        sysn = [n for n in names if installs.get(n, "user") != "user"]
        usern = [n for n in names if n not in sysn]
        cmds = []
        if usern:
            cmds.append(["flatpak", "uninstall", "--user", "-y"] + usern)
        if sysn:
            cmds.append(["pkexec", "flatpak", "uninstall", "--system", "-y"] + sysn)
        return cmds
