#!/bin/sh
# Сборка pkgsweep_<версия>_all.deb через dpkg-deb
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
V=$(sed -n 's/__version__ = "\(.*\)"/\1/p' "$SRC/pkgsweep/__init__.py")
T=$(mktemp -d)
D="$T/pkgsweep_${V}_all"
mkdir -p "$D/DEBIAN" "$D/usr/lib/pkgsweep" "$D/usr/bin" "$D/usr/share/applications" "$D/usr/share/icons/hicolor/scalable/apps"
cp -r "$SRC/pkgsweep" "$D/usr/lib/pkgsweep/"
find "$D" -name __pycache__ -prune -exec rm -rf {} +
install -m 755 "$SRC/bin/pkgsweep" "$D/usr/bin/pkgsweep"
install -m 644 "$SRC/data/io.github.drtiget.PkgSweep.desktop" "$D/usr/share/applications/"
install -m 644 "$SRC/data/io.github.drtiget.PkgSweep.svg" "$D/usr/share/icons/hicolor/scalable/apps/"
cat > "$D/DEBIAN/control" <<EOF
Package: pkgsweep
Version: $V
Section: admin
Priority: optional
Architecture: all
Depends: python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1, policykit-1 | pkexec
Maintainer: DrTiget <https://github.com/DrTiget>
Description: Менеджер установленных программ (APT, Snap, Flatpak)
 Единый список пакетов, поиск и безопасное удаление с предпросмотром.
EOF
dpkg-deb --build --root-owner-group "$D" "$SRC/pkgsweep_${V}_all.deb"
rm -rf "$T"
