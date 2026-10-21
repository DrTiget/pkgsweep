import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango  # noqa: E402

from ..backends import all_backends  # noqa: E402
from ..backends.apt import AptBackend  # noqa: E402
from ..backends.flatpak import FlatpakBackend  # noqa: E402
from ..backends.flatpak import export_icon_dirs  # noqa: E402
from ..enrich import enrich  # noqa: E402
from ..model import cmp, cmp_date, fmt_date, fmt_size, selected as sel_of, summary  # noqa: E402
from .runner import run_commands  # noqa: E402

SOURCES = [("all", "Все источники"), ("apt", "APT"), ("snap", "Snap"), ("flatpak", "Flatpak")]


class Item(GObject.Object):
    """Обёртка Package для Gio.ListStore. Состояние выбора живёт в pkg.selected (модель),
    а не в виджете: строки ColumnView переиспользуются."""
    rev = GObject.Property(type=int, default=0)  # растёт, когда фон дополнил метаданные

    def __init__(self, pkg):
        super().__init__()
        self.pkg = pkg

    @GObject.Property(type=bool, default=False)
    def selected(self):
        return self.pkg.selected

    @selected.setter
    def selected(self, v):
        self.pkg.selected = bool(v)


class LogWindow(Gtk.Window):
    def __init__(self, parent, on_close_ok):
        super().__init__(title="Журнал удаления", transient_for=parent, modal=True,
                         default_width=700, default_height=450)
        self.on_close_ok = on_close_ok
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.buf = Gtk.TextBuffer()
        tv = Gtk.TextView(buffer=self.buf, editable=False, monospace=True,
                          left_margin=8, right_margin=8)
        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_child(tv)
        self.tv = tv
        self.btn = Gtk.Button(label="Выполняется…", sensitive=False, margin_top=6,
                              margin_bottom=6, margin_start=6, margin_end=6)
        self.btn.connect("clicked", lambda *_: self.close())
        box.append(sw)
        box.append(self.btn)
        self.set_child(box)
        self.set_deletable(False)

    def add(self, text):
        self.buf.insert(self.buf.get_end_iter(), text)
        self.tv.scroll_to_mark(self.buf.create_mark(None, self.buf.get_end_iter(), False), 0, False, 0, 0)

    def finish(self, ok):
        self.btn.set_label("Закрыть" if ok else "Закрыть (были ошибки)")
        self.btn.set_sensitive(True)
        self.set_deletable(True)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Менеджер программ", default_width=1100, default_height=700)
        self.backends = all_backends()
        self.store = Gio.ListStore.new(Item)
        self.theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        for d in export_icon_dirs():
            self.theme.add_search_path(d)
        self._gen = 0
        self.manual_only = True
        self.source = "all"
        self.query = ""
        self._build()
        self.reload()

    # ---------- UI ----------
    def _build(self):
        tv = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.search = Gtk.SearchEntry(placeholder_text="Поиск по имени и описанию", hexpand=True)
        self.search.connect("search-changed", self._on_search)
        header.set_title_widget(self.search)
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Обновить список")
        refresh.connect("clicked", lambda *_: self.reload())
        header.pack_start(refresh)
        self.del_btn = Gtk.Button(label="Удалить", sensitive=False)
        self.del_btn.add_css_class("destructive-action")
        self.del_btn.connect("clicked", self._on_delete)
        header.pack_end(self.del_btn)
        tv.add_top_bar(header)

        bar = Gtk.Box(spacing=12, margin_top=6, margin_bottom=6, margin_start=12, margin_end=12)
        self.dd = Gtk.DropDown.new_from_strings([l for _, l in SOURCES])
        self.dd.connect("notify::selected", self._on_source)
        bar.append(self.dd)
        self.sw = Gtk.Switch(active=True, valign=Gtk.Align.CENTER)
        self.sw.connect("notify::active", self._on_manual)
        bar.append(self.sw)
        bar.append(Gtk.Label(label="Только установленные вручную"))
        self.total = Gtk.Label(hexpand=True, halign=Gtk.Align.END)
        bar.append(self.total)

        self.filter = Gtk.CustomFilter.new(self._match)
        fm = Gtk.FilterListModel(model=self.store, filter=self.filter)
        self.view = Gtk.ColumnView(show_row_separators=True)
        self.sorted = Gtk.SortListModel(model=fm, sorter=self.view.get_sorter())
        self.view.set_model(Gtk.NoSelection(model=self.sorted))
        self._columns()

        self.status = Gtk.Label(label="Загрузка…", xalign=0, margin_start=12, margin_bottom=4)
        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_child(self.view)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for w in (bar, sw, self.status):
            box.append(w)
        tv.set_content(box)
        self.set_content(tv)

    def _col(self, title, setup, update, sorter=None, expand=False, fixed=0):
        """Колонка: update(widget, item) вызывается при bind и при notify::rev (дозагрузка метаданных)."""
        f = Gtk.SignalListItemFactory()
        f.connect("setup", lambda _, li: setup(li))

        def bind(_, li):
            w, item = li.get_child(), li.get_item()
            update(w, item)
            w._h = item.connect("notify::rev", lambda it, _p: update(w, it))
            w._it = item

        def unbind(_, li):
            w = li.get_child()
            if getattr(w, "_h", None):
                w._it.disconnect(w._h)
                w._h = w._it = None

        f.connect("bind", bind)
        f.connect("unbind", unbind)
        c = Gtk.ColumnViewColumn(title=title, factory=f, expand=expand)
        if fixed:
            c.set_fixed_width(fixed)
        if sorter:
            c.set_sorter(sorter)
        self.view.append_column(c)
        return c

    def _columns(self):
        # --- чекбокс: активность берём из модели в bind, обработчик снимаем в unbind ---
        def chk_setup(_, li):
            li.set_child(Gtk.CheckButton())

        def chk_bind(_, li):
            cb, item = li.get_child(), li.get_item()
            cb.set_active(item.pkg.selected)          # сначала состояние, потом обработчик
            cb._item = item
            cb._h = cb.connect("toggled", lambda c: c._item.set_property("selected", c.get_active()))

        def chk_unbind(_, li):
            cb = li.get_child()
            if getattr(cb, "_h", None):
                cb.disconnect(cb._h)
                cb._h = None
            cb._item = None

        f = Gtk.SignalListItemFactory()
        f.connect("setup", chk_setup)
        f.connect("bind", chk_bind)
        f.connect("unbind", chk_unbind)
        self.view.append_column(Gtk.ColumnViewColumn(title="", factory=f, fixed_width=40))

        def name_setup(li):
            b = Gtk.Box(spacing=8)
            img = Gtk.Image(pixel_size=32)
            b.append(img)
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
            top = Gtk.Box(spacing=4)
            top.append(Gtk.Image(icon_name="changes-prevent-symbolic", visible=False,
                                 tooltip_text="Системный пакет — удаление опасно"))
            top.append(Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END))
            sub = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
            sub.add_css_class("dim-label")
            sub.add_css_class("caption")
            v.append(top)
            v.append(sub)
            b.append(v)
            li.set_child(b)

        def name_update(b, item):
            p = item.pkg
            img = b.get_first_child()
            self._set_icon(img, p.icon)
            v = img.get_next_sibling()
            top, sub = v.get_first_child(), v.get_last_child()
            top.get_first_child().set_visible(p.protected)
            top.get_last_child().set_text(p.title)
            sub.set_text(p.name if p.title != p.name else "")
            sub.set_visible(p.title != p.name)

        self._col("Имя", name_setup, name_update,
                  Gtk.CustomSorter.new(lambda a, b, _: cmp(a.pkg.title.lower(), b.pkg.title.lower())), fixed=300)

        def badge_setup(li):
            l = Gtk.Label(xalign=0)
            l.add_css_class("caption-heading")
            l.add_css_class("accent")
            li.set_child(l)

        self._col("Источник", badge_setup, lambda l, i: l.set_text(i.pkg.source.upper()), fixed=90)

        def lab_setup(li):
            li.set_child(Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END))

        self._col("Версия", lab_setup, lambda l, i: l.set_text(i.pkg.version), fixed=130)
        self._col("Размер", lab_setup, lambda l, i: l.set_text(fmt_size(i.pkg.size)),
                  Gtk.CustomSorter.new(lambda a, b, _: cmp(a.pkg.size, b.pkg.size)), fixed=90)
        self._col("Установлено", lab_setup, lambda l, i: l.set_text(fmt_date(i.pkg.installed)),
                  Gtk.CustomSorter.new(lambda a, b, _: cmp_date(a.pkg.installed, b.pkg.installed)), fixed=110)
        self._col("Использовано", lab_setup, lambda l, i: l.set_text(fmt_date(i.pkg.last_used)),
                  Gtk.CustomSorter.new(lambda a, b, _: cmp_date(a.pkg.last_used, b.pkg.last_used)), fixed=120)
        self._col("Описание", lab_setup, lambda l, i: l.set_text(i.pkg.description), expand=True)

    def _set_icon(self, img, icon):
        if icon.startswith("/"):
            if os.path.exists(icon):
                img.set_from_gicon(Gio.FileIcon.new(Gio.File.new_for_path(icon)))
                return
        elif icon and self.theme.has_icon(icon):
            img.set_from_icon_name(icon)
            return
        img.set_from_icon_name("package-x-generic")

    # ---------- данные ----------
    def reload(self):
        self.status.set_text("Загрузка списка пакетов…")
        self.store.remove_all()
        self._gen += 1
        gen = self._gen

        def work():
            pkgs = []
            for b in self.backends:
                try:
                    pkgs += b.list()
                except Exception as e:  # источник не должен ронять приложение
                    print("backend", b.source, e)
            GLib.idle_add(self._loaded, pkgs, gen)
            # тяжёлый сбор (dpkg.log, .desktop, иконки) — после показа списка
            enrich(pkgs, self.backends, lambda src: GLib.idle_add(self._enriched, gen))

        threading.Thread(target=work, daemon=True).start()

    def _loaded(self, pkgs, gen):
        if gen != self._gen:
            return
        items = [Item(p) for p in pkgs]
        for it in items:
            it.connect("notify::selected", lambda *_: self._update_total())
        self.store.splice(0, 0, items)
        self._refilter()

    def _enriched(self, gen):
        if gen != self._gen:
            return
        for it in self.store:
            it.props.rev += 1
        self.view.get_sorter().changed(Gtk.SorterChange.DIFFERENT)
        self._refilter()

    def _match(self, item):
        p = item.pkg
        if self.manual_only and not p.manual:
            return False
        if self.source != "all" and p.source != self.source:
            return False
        q = self.query
        return not q or q in p.title.lower() or q in p.name.lower() or q in p.description.lower()

    def _refilter(self):
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_total()

    def _on_search(self, e):
        self.query = e.get_text().strip().lower()
        self._refilter()

    def _on_source(self, dd, _):
        self.source = SOURCES[dd.get_selected()][0]
        self._refilter()

    def _on_manual(self, sw, _):
        self.manual_only = sw.get_active()
        self._refilter()

    def _selected(self):
        return sel_of([i.pkg for i in self.store])

    def _update_total(self):
        sel = self._selected()
        self.del_btn.set_sensitive(bool(sel))
        n, size = summary([i.pkg for i in self.store])
        self.total.set_text(f"Выбрано: {n}, суммарно {fmt_size(size)}")
        self.status.set_text(f"Показано: {self.sorted.get_n_items()} из {self.store.get_n_items()}")

    # ---------- удаление ----------
    def _on_delete(self, *_):
        sel = self._selected()
        self.del_btn.set_sensitive(False)
        self.status.set_text("Симуляция удаления…")

        def work():
            apt = [p.name for p in sel if p.source == "apt"]
            sim = AptBackend().simulate_remove(apt) if apt else None
            GLib.idle_add(self._confirm, sel, sim)

        threading.Thread(target=work, daemon=True).start()

    def _confirm(self, sel, sim):
        self._update_total()
        lines = []
        crit = bool(sim and sim.critical) or any(p.protected for p in sel)
        if sim:
            lines.append(f"APT — будет удалено пакетов: {len(sim.removed)}\n" + ", ".join(sim.removed))
            if sim.error:
                lines.append("⚠ " + sim.error)
        for src in ("snap", "flatpak"):
            names = [p.title for p in sel if p.source == src]
            if names:
                lines.append(f"{src.capitalize()}: " + ", ".join(names))
        dlg = Adw.AlertDialog(heading="Удалить выбранное?", body="Проверьте список перед удалением.")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tv = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD_CHAR, monospace=True)
        tv.get_buffer().set_text("\n\n".join(lines))
        sw = Gtk.ScrolledWindow(min_content_height=200, min_content_width=480)
        sw.set_child(tv)
        box.append(sw)
        dlg.add_response("cancel", "Отмена")
        dlg.add_response("remove", "Удалить")
        dlg.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        if crit:
            names = sorted(set((sim.critical if sim else []) + [p.name for p in sel if p.protected]))
            warn = Gtk.Label(wrap=True, xalign=0,
                             label="⚠ ОПАСНО: затронуты критичные системные пакеты: " + ", ".join(names) +
                                   ". Система может перестать загружаться.")
            warn.add_css_class("error")
            box.append(warn)
            ack = Gtk.CheckButton(label="Я понимаю")
            ack.connect("toggled", lambda c: dlg.set_response_enabled("remove", c.get_active()))
            box.append(ack)
            dlg.set_response_enabled("remove", False)
        dlg.set_extra_child(box)
        dlg.connect("response", lambda d, r: self._do_remove(sel) if r == "remove" else None)
        dlg.present(self)

    def _do_remove(self, sel):
        cmds = []
        apt = [p.name for p in sel if p.source == "apt"]
        if apt:
            cmds += AptBackend().remove_cmd(apt)
        by = {b.source: b for b in self.backends}
        snaps = [p.name for p in sel if p.source == "snap"]
        if snaps:
            cmds += by["snap"].remove_cmd(snaps)
        fl = [p for p in sel if p.source == "flatpak"]
        if fl:
            cmds += FlatpakBackend().remove_cmd([p.name for p in fl],
                                                {p.name: p.extra.get("installation", "user") for p in fl})
        log = LogWindow(self, None)
        log.present()
        run_commands(cmds, log.add, lambda ok: self._after(log, ok, bool(apt)))

    def _after(self, log, ok, was_apt):
        log.finish(ok)
        self.reload()
        if was_apt and ok:
            dlg = Adw.AlertDialog(heading="Выполнить autoremove?",
                                  body="Удалить ставшие ненужными зависимости (apt autoremove --purge)?")
            dlg.add_response("no", "Нет")
            dlg.add_response("yes", "Выполнить")
            dlg.connect("response", lambda d, r: self._autoremove() if r == "yes" else None)
            dlg.present(log)

    def _autoremove(self):
        log = LogWindow(self, None)
        log.present()
        run_commands(AptBackend().autoremove_cmd(), log.add, lambda ok: (log.finish(ok), self.reload()))


class App(Adw.Application):
    def __init__(self):
        GLib.set_prgname("io.github.drtiget.PkgSweep")
        super().__init__(application_id="io.github.drtiget.PkgSweep")

    def do_activate(self):
        (self.props.active_window or MainWindow(self)).present()
