#!/usr/bin/env bash
# Установка PkgSweep в ~/.local.
#   curl -fsSL https://raw.githubusercontent.com/DrTiget/pkgsweep/main/install.sh | bash
#   ... | bash -s -- --uninstall        (или ./install.sh --uninstall)
# Переменные: PREFIX (по умолчанию ~/.local), PKGSWEEP_REF (ветка/тег, main),
#             PKGSWEEP_TARBALL_URL (свой архив), PKGSWEEP_SKIP_DEPS=1 (не ставить зависимости).
set -euo pipefail

ID="io.github.drtiget.PkgSweep"
REPO="DrTiget/pkgsweep"
REF="${PKGSWEEP_REF:-main}"
P="${PREFIX:-$HOME/.local}"
APP="$P/share/pkgsweep"
DESKTOP="$P/share/applications/$ID.desktop"
ICON="$P/share/icons/hicolor/scalable/apps/$ID.svg"

refresh_caches() {
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$P/share/applications" >/dev/null 2>&1 || true
  if command -v gtk4-update-icon-cache >/dev/null 2>&1; then
    gtk4-update-icon-cache -q -t -f "$P/share/icons/hicolor" >/dev/null 2>&1 || true
  elif command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f "$P/share/icons/hicolor" >/dev/null 2>&1 || true
  fi
}

if [ "${1:-}" = "--uninstall" ]; then
  rm -rf "$APP" "$P/lib/pkgsweep"           # lib/ — раскладка версии 0.1
  rm -f "$P/bin/pkgsweep" "$DESKTOP" "$ICON"
  refresh_caches
  echo "PkgSweep удалён."
  exit 0
fi

# --- зависимости ---
have_deps() {
  python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" >/dev/null 2>&1
}
if [ "${PKGSWEEP_SKIP_DEPS:-0}" != "1" ] && ! have_deps; then
  echo "Устанавливаю зависимости: python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 (нужен sudo)…"
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
  else
    echo "Не найден apt — установите PyGObject, GTK4 и libadwaita вручную." >&2
    exit 1
  fi
fi

# --- исходники: локальный клон или скачанный архив ---
SELF="${BASH_SOURCE[0]:-}"
SRC=""
if [ -n "$SELF" ] && [ -f "$SELF" ] && [ -d "$(dirname "$SELF")/pkgsweep" ]; then
  SRC="$(cd "$(dirname "$SELF")" && pwd)"
else
  command -v curl >/dev/null 2>&1 || { echo "Нужен curl." >&2; exit 1; }
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  URL="${PKGSWEEP_TARBALL_URL:-https://github.com/$REPO/archive/$REF.tar.gz}"
  echo "Скачиваю $URL …"
  curl -fsSL "$URL" -o "$TMP/src.tar.gz"
  mkdir "$TMP/src"
  tar -xzf "$TMP/src.tar.gz" -C "$TMP/src" --strip-components=1
  SRC="$TMP/src"
fi

# --- установка ---
rm -rf "$APP" "$P/lib/pkgsweep"
mkdir -p "$APP" "$P/bin" "$P/share/applications" "$P/share/icons/hicolor/scalable/apps"
cp -r "$SRC/pkgsweep" "$SRC/bin" "$SRC/data" "$APP/"
find "$APP" -name __pycache__ -prune -exec rm -rf {} +
chmod 755 "$APP/bin/pkgsweep"
ln -sf "$APP/bin/pkgsweep" "$P/bin/pkgsweep"

# .desktop с абсолютным Exec
sed "s|^Exec=.*|Exec=$P/bin/pkgsweep|" "$SRC/data/$ID.desktop" > "$DESKTOP"
chmod 644 "$DESKTOP"
install -m 644 "$SRC/data/$ID.svg" "$ICON"
refresh_caches

echo "Готово. PkgSweep установлен в $APP и появится в меню приложений (при необходимости перезайдите в сессию)."
case ":$PATH:" in *":$P/bin:"*) ;; *) echo "Подсказка: добавьте $P/bin в PATH для запуска командой pkgsweep." ;; esac
