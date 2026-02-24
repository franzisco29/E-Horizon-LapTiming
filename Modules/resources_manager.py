from __future__ import annotations

from pathlib import Path
from PySide6.QtGui import QFontDatabase

_loaded = False


def load_fonts_once(fonts_dir: Path | None = None) -> None:
    """
    Carica TUTTI i .ttf in resources/fonts una sola volta.
    - Safe: se chiamata più volte non ricarica.
    - Robust: path assoluto basato sulla root progetto.
    """
    global _loaded
    if _loaded:
        return

    if fonts_dir is None:
        # Path relativo al progetto: .../<project_root>/resources/fonts
        project_root = Path(__file__).resolve().parents[1]
        fonts_dir = project_root / "resources" / "fonts"

    if not fonts_dir.exists():
        _loaded = True  # evita retry infinito
        return

    for f in fonts_dir.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))

    _loaded = True

from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget


def load_favicon(
    widget: QWidget | None = None,
    icon_name: str = "favicon.ico",
    base_path: str | Path = "resources/icons",
) -> QIcon:
    """
    Carica l'icona dell'applicazione (globalmente o per singola finestra).

    Parameters
    ----------
    widget : QWidget | None
        Se passato, imposta l'icona solo su quella finestra.
        Se None, imposta l'icona globalmente su QApplication.
    icon_name : str
        Nome del file icona.
    base_path : str | Path
        Cartella dove si trovano le icone.

    Returns
    -------
    QIcon
        L'oggetto icona caricato.
    """

    icon_path = Path(base_path) / icon_name

    if not icon_path.exists():
        print(f"[WARN] Icona non trovata: {icon_path}")
        return QIcon()

    icon = QIcon(str(icon_path))

    if widget:
        widget.setWindowIcon(icon)
    else:
        app = QApplication.instance()
        if app:
            app.setWindowIcon(icon)

    return icon
