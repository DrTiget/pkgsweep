import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pkgsweep.backends import apt, flatpak, snap  # noqa: E402

FX = os.path.join(os.path.dirname(__file__), "fixtures")


def fx(n):
    with open(os.path.join(FX, n), encoding="utf-8") as f:
        return f.read()


def test_apt_parse():
    pk = {p.name: p for p in apt.parse_query(fx("dpkg_query.txt"), apt.parse_manual(fx("manual.txt")), kernel="6.8.0-31-generic")}
    assert "oldpkg" not in pk  # статус rc пропускается
    assert pk["vlc"].size == 2048 * 1024 and pk["vlc"].manual and not pk["vlc"].protected
    assert not pk["libvlc5:amd64"].manual
    assert pk["bash"].protected  # essential/required
    assert pk["gnome-shell"].protected
    assert pk["linux-image-6.8.0-31-generic"].protected  # текущее ядро


def test_apt_old_kernel_not_protected():
    assert not apt.is_critical("linux-image-6.5.0-1-generic", "optional", False, kernel="6.8.0-31-generic")


def test_apt_simulation():
    assert apt.parse_simulation(fx("apt_sim.txt")) == ["vlc", "libvlc5:amd64", "ubuntu-desktop"]
    assert apt.is_critical("ubuntu-desktop")
    assert apt.is_critical("ubuntu-desktop-minimal")
    assert not apt.is_critical("vlc", "optional", False)


def test_snap_parse():
    e = {x["name"]: x for x in snap.parse_list(fx("snap_list.txt"))}
    assert set(e) == {"core22", "firefox", "gnome-42-2204", "snapd"}
    assert e["firefox"]["rev"] == "4033"
    assert snap.is_system("core22") and snap.is_system("gnome-42-2204") and snap.is_system("mesa-core22")
    assert not snap.is_system("firefox")


def test_snap_summary():
    assert snap.parse_info_summary("name: x\nsummary: Web browser\n") == "Web browser"


def test_flatpak_parse():
    a = flatpak.parse_list(fx("flatpak_apps.txt"), False)
    assert a[0].name == "org.gimp.GIMP" and a[0].display_name == "GIMP" and a[0].manual
    assert a[0].size == 1_200_000_000 and a[1].size == 350_500_000
    r = flatpak.parse_list(fx("flatpak_rt.txt"), True)
    assert not r[0].manual and r[0].extra["installation"] == "system"


def test_flatpak_remove_cmd():
    cmds = flatpak.FlatpakBackend().remove_cmd(["a", "b"], {"a": "user", "b": "system"})
    assert cmds[0][:2] == ["flatpak", "uninstall"] and cmds[1][0] == "pkexec"


def test_remove_cmds():
    assert apt.AptBackend().remove_cmd(["x"]) == [["pkexec", "apt-get", "-y", "purge", "x"]]
    assert snap.SnapBackend().remove_cmd(["x"]) == [["pkexec", "snap", "remove", "x"]]


# ---------- v0.2: метаданные ----------
import gzip  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

from pkgsweep import enrich as enrich_mod  # noqa: E402
from pkgsweep import model  # noqa: E402
from pkgsweep.backends import meta  # noqa: E402
from pkgsweep.backends.base import Package  # noqa: E402


def test_user_langs():
    assert meta.user_langs({"LANG": "ru_RU.UTF-8"}) == ["ru_RU", "ru"]
    assert meta.user_langs({"LANGUAGE": "ru:en", "LANG": "C"}) == ["ru", "en"]
    assert meta.user_langs({"LANG": "C.UTF-8"}) == []


def test_desktop_locale():
    t = fx("app_ru.desktop")
    d = meta.parse_desktop(t, ["ru_RU", "ru"])
    assert d["name"] == "Просмотр изображений" and d["comment"].startswith("Просмотр и печать")
    assert d["icon"] == "org.gnome.eog" and not d["nodisplay"]
    en = meta.parse_desktop(t, [])
    assert en["name"] == "Image Viewer" and en["comment"] == "View images"
    assert meta.parse_desktop(t, ["de"])["name"] == "Bildbetrachter"
    assert meta.parse_desktop(t, ["de"])["comment"] == "View images"  # нет Comment[de] -> базовый


def test_desktop_ignores_actions_and_pick():
    d = meta.parse_desktop(fx("app_ru.desktop"), ["ru"])
    assert d["name"] != "Действие"
    hid = meta.parse_desktop(fx("hidden.desktop"))
    assert hid["nodisplay"]
    assert meta.pick_desktop([hid, d]) is d
    assert meta.pick_desktop([hid]) is hid
    assert meta.pick_desktop([]) is None


def test_exec_program():
    assert meta.exec_program("env GDK_BACKEND=x11 /usr/bin/eog --new-window %U") == "/usr/bin/eog"
    assert meta.exec_program('"/opt/My App/run" %f') == "/opt/My App/run"
    assert meta.exec_program("%U") is None


def test_resolve_icon():
    assert meta.resolve_icon("${SNAP}/meta/gui/icon.png", "/snap/x/current") == "/snap/x/current/meta/gui/icon.png"
    assert meta.resolve_icon("org.gnome.eog") == "org.gnome.eog" and meta.resolve_icon("") == ""


def test_dpkg_log_first_install():
    log = meta.parse_dpkg_log(fx("dpkg.log").splitlines())
    assert set(log) == {"vlc", "curl"}  # upgrade/status игнорируются, арх. отрезан
    assert log["vlc"] == time.mktime((2024, 2, 1, 8, 30, 0, 0, 0, -1))


def test_dpkg_log_gz_and_rotation():
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "dpkg.log"), "w") as f:
            f.write("2024-05-01 10:00:00 install new <none> 1\n")
        with gzip.open(os.path.join(d, "dpkg.log.2.gz"), "wt") as f:
            f.write("2023-01-01 00:00:00 install new:amd64 <none> 1\n")
        log = meta.read_dpkg_logs(os.path.join(d, "dpkg.log*"))
        assert log["new"] == time.mktime((2023, 1, 1, 0, 0, 0, 0, 0, -1))
    finally:
        shutil.rmtree(d)


def test_translation():
    tr = meta.parse_translation(fx("translation_ru.txt"))
    assert tr["vlc"] == "многофункциональный медиаплеер" and len(tr) == 2


def test_snap_yaml_and_collect():
    assert meta.parse_snap_yaml(fx("snap.yaml"))["title"] == "Firefox Web Browser"
    d = tempfile.mkdtemp()
    try:
        cur = os.path.join(d, "root", "firefox", "current", "meta")
        os.makedirs(os.path.join(cur, "gui"))
        shutil.copy(os.path.join(FX, "snap.yaml"), cur)
        shutil.copy(os.path.join(FX, "app_ru.desktop"), os.path.join(cur, "gui", "firefox.desktop"))
        info = snap.collect_one("firefox", "1", ["ru"], root=os.path.join(d, "root"),
                                snaps=os.path.join(d, "none"), exported=os.path.join(d, "none2"))
        assert info["display_name"] == "Просмотр изображений"
        assert info["description"].startswith("Просмотр и печать")
        assert "installed" in info  # mtime /snap/<name>
    finally:
        shutil.rmtree(d)


def test_snap_title_fallback_without_desktop():
    d = tempfile.mkdtemp()
    try:
        cur = os.path.join(d, "firefox", "current", "meta")
        os.makedirs(cur)
        shutil.copy(os.path.join(FX, "snap.yaml"), cur)
        info = snap.collect_one("firefox", "1", [], root=d, snaps=d + "/x", exported=d + "/y")
        assert info["display_name"] == "Firefox Web Browser" and info["description"] == "Mozilla Firefox web browser"
    finally:
        shutil.rmtree(d)


def test_flatpak_description_column():
    rows = flatpak.parse_list("org.a.B\tB App\t1\t1 MB\tuser\tПростое приложение\n", False)
    assert rows[0].description == "Простое приложение" and rows[0].extra["installation"] == "user"


def test_last_used_atime():
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "bin")
        open(p, "w").close()
        os.utime(p, (1000, 1000))
        assert meta.last_used_from_atime(p) is None  # не читали после установки
        os.utime(p, (5000000, 1000))
        assert meta.last_used_from_atime(p) == 5000000
        assert meta.last_used_from_atime(os.path.join(d, "nope")) is None
    finally:
        shutil.rmtree(d)


def test_selection_is_per_package():
    """Регрессия: одна галочка не должна отмечать другие строки."""
    pkgs = [Package(name=f"p{i}", source="apt", size=100 * (i + 1)) for i in range(5)]
    model.set_selected(pkgs[2], True)
    assert [p.name for p in model.selected(pkgs)] == ["p2"]
    assert model.summary(pkgs) == (1, 300)
    model.set_selected(pkgs[2], False)
    assert model.summary(pkgs) == (0, 0)


def test_dates_and_sorting():
    assert model.fmt_date(None) == "неизвестно"
    assert model.fmt_date(time.mktime((2024, 2, 1, 12, 0, 0, 0, 0, -1))) == "01.02.2024"
    assert model.cmp_date(None, 5) == -1 and model.cmp_date(None, None) == 0 and model.cmp_date(9, 5) == 1


class FakeBackend:
    source = "apt"
    calls = 0

    def collect(self, pkgs):
        FakeBackend.calls += 1
        return {p.name: {"display_name": "Nice " + p.name, "installed": 42.0} for p in pkgs}


def test_enrich_cache():
    enrich_mod._CACHE.clear()
    pkgs = [Package(name="a", source="apt", description="eng")]
    enrich_mod.enrich(pkgs, [FakeBackend()])
    enrich_mod.enrich(pkgs, [FakeBackend()])
    assert FakeBackend.calls == 1  # второй раз — из кэша
    assert pkgs[0].title == "Nice a" and pkgs[0].installed == 42.0 and pkgs[0].description == "eng"
