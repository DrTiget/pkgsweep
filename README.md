# PkgSweep — менеджер установленных программ

Десктопное приложение для Ubuntu 26.04 (GNOME): единый список пакетов APT, Snap и Flatpak,
поиск, фильтры, безопасное удаление с предпросмотром. Python 3 + GTK4 + libadwaita.

> ⚠️ Версия 0.1 — ранняя. Интерфейс пока не проверен на реальной Ubuntu 26.04, баги — в Issues.

![Ubuntu 26.04](https://img.shields.io/badge/Ubuntu-26.04-E95420?logo=ubuntu&logoColor=white) ![GTK4](https://img.shields.io/badge/GTK-4%20%2B%20libadwaita-4A86CF) ![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Быстрый старт

    sudo apt install git python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
    git clone https://github.com/DrTiget/pkgsweep.git
    cd pkgsweep
    ./install.sh          # появится в меню приложений как «PkgSweep»

## Зависимости

    sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1

Snap и Flatpak необязательны — если не установлены, источник пропускается.

## Запуск

Из каталога проекта: `python3 -m pkgsweep` или `bin/pkgsweep`.

## Установка

- В `~/.local`: `./install.sh` (удаление: `./install.sh --uninstall`).
- Пакет .deb: `./build-deb.sh`, затем `sudo apt install ./pkgsweep_0.1.0_all.deb`.

## Возможности

- Колонки: имя, источник (бейдж), версия, размер, описание; сортировка по имени и размеру (клик по заголовку).
- Живой поиск по имени и описанию; фильтр по источнику.
- Переключатель «Только установленные вручную» (по умолчанию включён): скрывает APT-зависимости,
  системные базы snap (core*, snapd, gnome-*, mesa-* …) и рантаймы Flatpak.
- Чекбоксы, итог суммарного размера выбранного.
- Удаление: диалог с симуляцией `apt-get -s purge` (показаны ВСЕ удаляемые пакеты), затем
  `pkexec apt-get -y purge`, `pkexec snap remove`, `flatpak uninstall -y` (system-установки — через pkexec).
  Вывод — в окне журнала, UI не блокируется. После APT-удаления предлагается `autoremove --purge`.
- Защита: пакеты Essential / Priority required|important и список (ubuntu-desktop*, gnome-shell, gdm3,
  systemd, network-manager, ядро текущей версии, sudo, apt, dpkg, snapd, xorg, pipewire, nautilus …)
  помечены замком; если симуляция их затрагивает — красное предупреждение, «Удалить» заблокировано до галочки «Я понимаю».

## Структура

`pkgsweep/backends/{apt,snap,flatpak}.py` — `list()`, `simulate_remove()`, `remove_cmd()`;
`pkgsweep/ui/` — окно; `tests/` — тесты парсинга.

## Тесты

    python3 -m pytest tests

## Тесты

    python3 -m pytest tests

## Лицензия

MIT — см. [LICENSE](LICENSE).
