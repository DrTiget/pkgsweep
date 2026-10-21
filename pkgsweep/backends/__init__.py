from .apt import AptBackend
from .flatpak import FlatpakBackend
from .snap import SnapBackend


def all_backends():
    return [b for b in (AptBackend(), SnapBackend(), FlatpakBackend()) if b.available()]
