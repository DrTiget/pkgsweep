# PkgSweep — менеджер установленных программ

Десктопное приложение для Ubuntu 26.04 (GNOME): единый список пакетов APT, Snap и Flatpak,
поиск, фильтры, безопасное удаление с предпросмотром. Python 3 + GTK4 + libadwaita.

> ⚠️ Версия 0.2 — ранняя. Интерфейс пока не проверен на реальной Ubuntu 26.04, баги — в Issues.

![Ubuntu 26.04](https://img.shields.io/badge/Ubuntu-26.04-E95420?logo=ubuntu&logoColor=white) ![GTK4](https://img.shields.io/badge/GTK-4%20%2B%20libadwaita-4A86CF) ![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Быстрый старт

    curl -fsSL https://raw.githubusercontent.com/DrTiget/pkgsweep/main/install.sh | bash

Скрипт сам скачает архив в `~/.local/share/pkgsweep`, при необходимости поставит
`python3-gi gir1.2-gtk-4.0 gir1.2-adw-1` через `sudo apt`, создаст ярлык в меню приложений и иконку.
Удаление: `curl -fsSL https://raw.githubusercontent.com/DrTiget/pkgsweep/main/install.sh | bash -s -- --uninstall`

Из клона репозитория то же самое делает `./install.sh`.

## Зависимости

    sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1

Snap и Flatpak необязательны — если не установлены, источник пропускается.

## Запуск

Из каталога проекта: `python3 -m pkgsweep` или `bin/pkgsweep`.

## Установка

- В `~/.local`: `./install.sh` (удаление: `./install.sh --uninstall`).
- Пакет .deb: `./build-deb.sh`, затем `sudo apt install ./pkgsweep_0.2.1_all.deb`.

## Возможности

- Колонки: иконка и название программы (имя пакета — мелким шрифтом ниже), источник (бейдж), версия, размер,
  дата установки, дата последнего использования, описание; сортировка кликом по заголовку (имя, размер, даты).
- Названия, описания и иконки берутся из `.desktop` пакета с учётом локали (`Name[ru]`, `Comment[ru]`);
  для APT без `.desktop` — перевод описания из `Translation-ru` в `/var/lib/apt/lists`, если он установлен;
  для Flatpak — локализованное описание из `flatpak list`. Иначе показывается имя пакета / английское описание.
- Тяжёлый сбор метаданных идёт в фоне после показа списка и кэшируется по имени пакета.
- Живой поиск по имени и описанию; фильтр по источнику.
- Переключатель «Только установленные вручную» (по умолчанию включён): скрывает APT-зависимости,
  системные базы snap (core*, snapd, gnome-*, mesa-* …) и рантаймы Flatpak.
- Фильтр «Показывать»: Программы / Программы и утилиты (по умолчанию) / Всё. Библиотеки (`lib*`, `*-dev`,
  `python3-*`, `gir1.2-*`, Section `libs` и т. п., snap-базы, рантаймы Flatpak) скрыты; в статусе — «скрыто N библиотек».
  Фильтр влияет только на список: симуляция удаления по-прежнему показывает все удаляемые библиотеки.
- Чекбоксы, итог суммарного размера выбранного.
- Удаление: диалог с симуляцией `apt-get -s purge` (показаны ВСЕ удаляемые пакеты), затем
  `pkexec apt-get -y purge`, `pkexec snap remove`, `flatpak uninstall -y` (system-установки — через pkexec).
  Вывод — в окне журнала, UI не блокируется. После APT-удаления предлагается `autoremove --purge`.
- Защита: пакеты Essential / Priority required|important и список (ubuntu-desktop*, gnome-shell, gdm3,
  systemd, network-manager, ядро текущей версии, sudo, apt, dpkg, snapd, xorg, pipewire, nautilus …)
  помечены замком; если симуляция их затрагивает — красное предупреждение, «Удалить» заблокировано до галочки «Я понимаю».

## Откуда берутся даты

- **Установка.** APT: самая ранняя запись `install` в `/var/log/dpkg.log*` (включая `.gz`), иначе mtime
  `/var/lib/dpkg/info/<пакет>.list`. Snap: mtime файла `/var/lib/snapd/snaps/<имя>_<rev>.snap`. Flatpak: mtime каталога установки.
  Если логи ротированы и удалены, у старых пакетов будет дата сборки образа/установки системы.
- **Последнее использование — приблизительно.** Берётся atime исполняемого файла из `Exec=` в `.desktop`
  (только APT). При монтировании с `relatime` (по умолчанию) atime обновляется не чаще раза в сутки,
  при `noatime` не обновляется вовсе; если файл не читали после установки, показывается «неизвестно».
  Для Snap и Flatpak дата использования недоступна.

## Структура

`pkgsweep/backends/{apt,snap,flatpak}.py` — `list()`, `simulate_remove()`, `remove_cmd()`;
`pkgsweep/backends/meta.py` — парсеры .desktop/dpkg.log/Translation; `pkgsweep/enrich.py` — фоновый сбор с кэшем;
`pkgsweep/model.py` — логика выбора и дат; `pkgsweep/ui/` — окно; `tests/` — тесты парсинга.

## Тесты

    python3 -m pytest tests

## Лицензия

MIT — см. [LICENSE](LICENSE).
