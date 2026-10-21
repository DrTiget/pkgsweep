"""Общая модель и интерфейс бэкендов."""
import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class Package:
    name: str            # идентификатор для удаления
    source: str          # apt | snap | flatpak
    version: str = ""
    size: int = 0        # байты
    description: str = ""
    manual: bool = True  # False -> зависимость/база/рантайм
    protected: bool = False
    display_name: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def title(self):
        return self.display_name or self.name


@dataclass
class Simulation:
    removed: list           # имена всех удаляемых пакетов (включая выбранные)
    critical: list          # критичные среди них
    error: str = ""


def run(cmd, env=None):
    """Запуск CLI с чтением вывода; возвращает (код, stdout)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""
    return p.returncode, p.stdout


class Backend:
    source = ""

    def available(self):
        return True

    def list(self):
        raise NotImplementedError

    def simulate_remove(self, names):
        return Simulation(removed=list(names), critical=[])

    def remove_cmd(self, names):
        """Список команд (argv), выполняемых по очереди."""
        raise NotImplementedError


def have(binary):
    return shutil.which(binary) is not None
