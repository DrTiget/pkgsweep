"""Выполнение команд в потоке с построчным выводом (UI не блокируется)."""
import subprocess
import threading

from gi.repository import GLib


def run_commands(cmds, on_line, on_done):
    """cmds — список argv; on_line(str) и on_done(ok: bool) вызываются в главном потоке."""
    def worker():
        ok = True
        for cmd in cmds:
            GLib.idle_add(on_line, "$ " + " ".join(cmd) + "\n")
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, bufsize=1)
                for line in p.stdout:
                    GLib.idle_add(on_line, line)
                rc = p.wait()
            except OSError as e:
                GLib.idle_add(on_line, f"Ошибка запуска: {e}\n")
                rc = 127
            if rc != 0:
                ok = False
                GLib.idle_add(on_line, f"[код возврата {rc}]\n")
        GLib.idle_add(on_done, ok)

    threading.Thread(target=worker, daemon=True).start()
