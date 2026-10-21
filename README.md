<div align="center">

<img src="data/io.github.drtiget.PkgSweep.svg" width="96" alt="PkgSweep">

# PkgSweep

**Удобное удаление программ в Ubuntu — APT, Snap и Flatpak в одном окне**

![Ubuntu 26.04](https://img.shields.io/badge/Ubuntu-26.04-E95420?logo=ubuntu&logoColor=white)
![GNOME](https://img.shields.io/badge/GNOME-GTK4%20%2B%20libadwaita-4A86CF?logo=gnome&logoColor=white)
![Python](https://img.shields.io/badge/Python-3-3776AB?logo=python&logoColor=white)
![Version](https://img.shields.io/badge/version-0.2.1-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

</div>

---

Чтобы удалить APT-пакет, нужно знать его точное имя, а «Центр приложений» показывает далеко не всё.
PkgSweep собирает все установленные программы в один список — с нормальными названиями, иконками,
размером и датами — и позволяет удалить лишнее в пару кликов, не сломав систему.

## ✨ Возможности

- 📦 **Всё в одном списке** — пакеты APT, Snap и Flatpak.
- 🏷️ **Человеческие названия и иконки** — «Firefox», а не `firefox`; описания на русском, если есть перевод.
- 🔍 **Поиск и фильтры** — живой поиск, фильтр по источнику, «только установленные вручную»,
  режим «Программы / Программы и утилиты / Всё» — библиотеки скрыты по умолчанию.
- 📊 **Размер и даты** — сортировка по размеру, дате установки и последнего использования.
- 🗑️ **Пакетное удаление** — отметьте несколько программ и удалите разом; итог освобождаемого места виден сразу.
- 👀 **Предпросмотр** — перед удалением показано *всё*, что уйдёт вместе с выбранным (включая скрытые библиотеки).
- 🛡️ **Защита системы** — ядро, `gnome-shell`, `systemd`, `apt`, `ubuntu-desktop` и другие критичные пакеты
  помечены замком; если удаление их затронет — красное предупреждение и блокировка до явного подтверждения.
- 🧹 **Уборка хвостов** — после удаления предлагается `apt autoremove --purge`.

## 🚀 Установка

Одна команда — скачает программу, при необходимости поставит зависимости и добавит ярлык в меню приложений:

```bash
curl -fsSL https://raw.githubusercontent.com/DrTiget/pkgsweep/main/install.sh | bash
```

После этого ищите **PkgSweep** в меню приложений. Та же команда обновляет программу до последней версии.

<details>
<summary>Удаление PkgSweep</summary>

```bash
curl -fsSL https://raw.githubusercontent.com/DrTiget/pkgsweep/main/install.sh | bash -s -- --uninstall
```
</details>

<details>
<summary>Установка из исходников / сборка .deb</summary>

```bash
sudo apt install git python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
git clone https://github.com/DrTiget/pkgsweep.git
cd pkgsweep
./install.sh                 # установка в ~/.local
# или запуск без установки:
python3 -m pkgsweep
# или пакет .deb:
./build-deb.sh && sudo apt install ./pkgsweep_0.2.1_all.deb
```
</details>

### Требования

- Ubuntu 26.04 (или другой дистрибутив с GNOME, GTK 4 и libadwaita)
- `python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1` — ставятся установщиком автоматически
- Snap и Flatpak — по желанию: если их нет, соответствующий источник просто не показывается

## 🧭 Как пользоваться

1. Откройте PkgSweep — список загрузится сразу, названия и иконки подтянутся за пару секунд.
2. Найдите ненужное поиском или отсортируйте по размеру.
3. Отметьте галочками и нажмите **«Удалить»**.
4. Проверьте список в окне предпросмотра и подтвердите — система спросит пароль.

> 💡 Если в предпросмотре появилось красное предупреждение — удаление заденет системные компоненты.
> Скорее всего, стоит отменить.

## ❓ Вопросы

<details>
<summary>Откуда берутся даты установки и использования?</summary>

- **Установка.** APT — из журнала `/var/log/dpkg.log*`, точная. Snap и Flatpak — по дате файлов, приблизительная.
- **Последнее использование** — только для APT-программ и приблизительно (с точностью до суток):
  по времени последнего чтения исполняемого файла. Для Snap и Flatpak эта дата недоступна.
</details>

<details>
<summary>Почему описание на английском?</summary>

Русское описание берётся из ярлыка программы или из переводов APT (`Translation-ru`).
Если перевода нет ни там, ни там — показывается оригинал.
</details>

<details>
<summary>Чем отличаются «программы», «утилиты» и «библиотеки»?</summary>

- **Программы** — всё, что есть в меню приложений.
- **Утилиты** — консольные инструменты, шрифты, драйверы и прочее.
- **Библиотеки** — `lib*`, `*-dev`, `python3-*`, `gir1.2-*`, рантаймы Flatpak, базы Snap. Обычно их не удаляют
  вручную — они уходят сами вместе с программами через `autoremove`.
</details>

## 🛠️ Разработка

```
pkgsweep/
├── backends/      # apt.py, snap.py, flatpak.py — list(), simulate_remove(), remove_cmd(); meta.py — парсеры
├── classify.py    # программа / утилита / библиотека
├── enrich.py      # фоновый сбор названий, иконок, дат (с кэшем)
├── model.py       # модель списка и выбора
└── ui/            # окно GTK4 + libadwaita
tests/             # тесты на фикстурах
```

```bash
python3 -m pytest tests
```

Правила участия — в [CONTRIBUTING.md](CONTRIBUTING.md), история изменений — в [CHANGELOG.md](CHANGELOG.md).

## 📄 Лицензия

[MIT](LICENSE) © DrTiget
