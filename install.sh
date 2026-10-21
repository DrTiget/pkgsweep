#!/bin/sh
# Установка в ~/.local (удаление: ./install.sh --uninstall)
set -e
P="${PREFIX:-$HOME/.local}"
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$1" = "--uninstall" ]; then
  rm -rf "$P/lib/pkgsweep" "$P/bin/pkgsweep" "$P/share/applications/io.github.drtiget.PkgSweep.desktop" \
         "$P/share/icons/hicolor/scalable/apps/io.github.drtiget.PkgSweep.svg"
  echo "Удалено."; exit 0
fi
mkdir -p "$P/lib/pkgsweep" "$P/bin" "$P/share/applications" "$P/share/icons/hicolor/scalable/apps"
rm -rf "$P/lib/pkgsweep/pkgsweep"
cp -r "$SRC/pkgsweep" "$P/lib/pkgsweep/"
find "$P/lib/pkgsweep" -name __pycache__ -prune -exec rm -rf {} +
install -m 755 "$SRC/bin/pkgsweep" "$P/bin/pkgsweep"
install -m 644 "$SRC/data/io.github.drtiget.PkgSweep.desktop" "$P/share/applications/"
install -m 644 "$SRC/data/io.github.drtiget.PkgSweep.svg" "$P/share/icons/hicolor/scalable/apps/"
command -v update-desktop-database >/dev/null && update-desktop-database "$P/share/applications" || true
command -v gtk4-update-icon-cache >/dev/null && gtk4-update-icon-cache -q -t "$P/share/icons/hicolor" || true
echo "Установлено в $P. Запуск: pkgsweep (убедитесь, что $P/bin в PATH)."
