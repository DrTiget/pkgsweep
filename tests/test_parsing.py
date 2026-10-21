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
