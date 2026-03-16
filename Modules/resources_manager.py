from __future__ import annotations

from pathlib import Path
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication, QWidget

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


def load_favicon(
    widget: QWidget | None = None,
    icon_name: str = "favicon.ico",
    root_path: str | Path | None = None,
) -> QIcon:
    """
    Carica l'icona dell'applicazione (globalmente o per singola finestra).

    Cerca l'icona in:
      1. <root_path>/Resources/icons/<icon_name>  (se root_path è fornito)
      2. <project_root>/Resources/icons/<icon_name>  (fallback dev)

    Parameters
    ----------
    widget : QWidget | None
        Se passato, imposta l'icona solo su quella finestra.
        Se None, imposta l'icona globalmente su QApplication.
    icon_name : str
        Nome del file icona (default: "favicon.ico").
    root_path : str | Path | None
        Root del progetto utente (es. da Settings.root_path).
    """
    candidates: list[Path] = []

    if root_path is not None:
        candidates.append(Path(root_path) / "Resources" / "icons" / icon_name)

    # Fallback: cartella Resources accanto al progetto
    project_root = Path(__file__).resolve().parents[1]
    candidates.append(project_root / "Resources" / "icons" / icon_name)

    icon_path: Path | None = next((p for p in candidates if p.exists()), None)

    if icon_path is None:
        print(f"[WARN] Icona non trovata: {icon_name}")
        return QIcon()

    icon = QIcon(str(icon_path))

    if widget:
        widget.setWindowIcon(icon)
    else:
        app = QApplication.instance()
        if app:
            app.setWindowIcon(icon)

    return icon
