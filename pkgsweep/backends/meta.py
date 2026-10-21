"""Чистые парсеры метаданных: .desktop с локалью, dpkg.log, Translation-*, snap.yaml."""
import bz2
import glob
import gzip
import lzma
import os
import re
import shlex
import shutil
import subprocess
import time


# ---------- локаль ----------
def user_langs(env=None):
    """['ru_RU', 'ru'] по LANGUAGE/LC_ALL/LC_MESSAGES/LANG (C/POSIX игнорируются)."""
    env = os.environ if env is None else env
    raw = []
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = env.get(var, "")
        if v:
            raw += v.split(":")
    langs = []
    for v in raw:
        v = re.split(r"[.@]", v)[0]
        if not v or v in ("C", "POSIX"):
            continue
        for cand in (v, v.split("_")[0]):
            if cand not in langs:
                langs.append(cand)
    return langs


# ---------- .desktop ----------
_KEY = re.compile(r"^([A-Za-z0-9-]+)(?:\[([^\]]+)\])?$")


def _unescape(v):
    return v.replace("\\s", " ").replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")


def parse_desktop(text, langs=()):
    """Секция [Desktop Entry] -> name/comment/generic/icon/exec/nodisplay (с учётом Key[lang])."""
    raw = {}
    in_entry = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            in_entry = line == "[Desktop Entry]"
            continue
        if not in_entry or "=" not in line:
            continue
        k, v = line.split("=", 1)
        m = _KEY.match(k.strip())
        if m:
            raw[(m.group(1), m.group(2))] = _unescape(v.strip())

    def loc(key):
        for lang in langs:
            if (key, lang) in raw:
                return raw[(key, lang)]
        return raw.get((key, None), "")

    return {
        "type": raw.get(("Type", None), ""),
        "name": loc("Name"),
        "comment": loc("Comment"),
        "generic": loc("GenericName"),
        "icon": raw.get(("Icon", None), ""),
        "exec": raw.get(("Exec", None), ""),
        "nodisplay": raw.get(("NoDisplay", None), "").lower() == "true"
        or raw.get(("Hidden", None), "").lower() == "true",
    }


def pick_desktop(entries):
    """Лучший из .desktop пакета: приложение, видимое, с именем."""
    good = [e for e in entries if e.get("name") and e.get("type", "Application") == "Application"]
    for e in good:
        if not e["nodisplay"]:
            return e
    return good[0] if good else None


def desktop_summary(entry):
    return entry.get("comment") or entry.get("generic") or ""


def exec_program(line):
    """Исполняемый файл из Exec= (без env, VAR=x, флагов и %-кодов)."""
    try:
        toks = shlex.split(line)
    except ValueError:
        toks = line.split()
    i = 0
    while i < len(toks) and (toks[i] == "env" or (re.match(r"^[A-Za-z_]\w*=", toks[i])) or
                             (i > 0 and toks[i - 1] == "env" and toks[i].startswith("-"))):
        i += 1
    if i >= len(toks) or toks[i].startswith("%"):
        return None
    prog = toks[i]
    if not os.path.isabs(prog):
        prog = shutil.which(prog)
    return prog


def last_used_from_atime(path, stat=os.stat):
    """atime исполняемого; если файл не читали после установки — None (неизвестно)."""
    try:
        path = os.path.realpath(path)
        st = stat(path)
    except (OSError, TypeError):
        return None
    if st.st_atime <= st.st_mtime + 60:
        return None
    return st.st_atime


# ---------- иконки ----------
def resolve_icon(icon, snap_dir=None):
    """Имя темы оставляем как есть; ${SNAP} -> каталог snap; пустое -> ''."""
    if not icon:
        return ""
    if snap_dir:
        icon = icon.replace("${SNAP}", snap_dir).replace("$SNAP", snap_dir)
    return icon


# ---------- dpkg.log ----------
_INSTALL = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) install (\S+) ")


def parse_dpkg_log(lines, into=None):
    """pkg -> время (epoch) самой ранней записи `install`."""
    res = {} if into is None else into
    for line in lines:
        m = _INSTALL.match(line)
        if not m:
            continue
        try:
            ts = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
        pkg = m.group(2).split(":")[0]
        if pkg not in res or ts < res[pkg]:
            res[pkg] = ts
    return res


def open_text(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    if path.endswith(".xz"):
        return lzma.open(path, "rt", encoding="utf-8", errors="replace")
    if path.endswith(".bz2"):
        return bz2.open(path, "rt", encoding="utf-8", errors="replace")
    if path.endswith(".lz4"):
        try:
            out = subprocess.run(["lz4", "-dc", path], capture_output=True, timeout=60).stdout
        except (OSError, subprocess.TimeoutExpired):
            raise OSError("lz4 недоступен")
        import io
        return io.StringIO(out.decode("utf-8", "replace"))
    return open(path, encoding="utf-8", errors="replace")


def read_dpkg_logs(pattern="/var/log/dpkg.log*"):
    res = {}
    for path in glob.glob(pattern):
        try:
            with open_text(path) as f:
                parse_dpkg_log(f, res)
        except OSError:
            continue
    return res


# ---------- переводы описаний apt ----------
def parse_translation(text, into=None):
    """Translation-<lang>: pkg -> первая строка Description-<lang>."""
    res = {} if into is None else into
    for block in re.split(r"\n\s*\n", text):
        pkg = desc = None
        lines = block.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("Package:"):
                pkg = line.split(":", 1)[1].strip()
            elif line.startswith("Description-"):
                desc = line.split(":", 1)[1].strip()
        if pkg and desc:
            res.setdefault(pkg, desc)
    return res


def read_translations(langs, pattern="/var/lib/apt/lists/*Translation-%s*"):
    for lang in langs:
        res = {}
        for path in glob.glob(pattern % lang):
            try:
                with open_text(path) as f:
                    parse_translation(f.read(), res)
            except OSError:
                continue
        if res:
            return res
    return {}


# ---------- snap.yaml ----------
def parse_snap_yaml(text):
    out = {}
    for key in ("name", "title", "summary"):
        m = re.search(r"^%s:\s*(.+?)\s*$" % key, text, re.M)
        if m:
            out[key] = m.group(1).strip("'\"")
    return out
