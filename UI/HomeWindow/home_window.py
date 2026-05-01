from __future__ import annotations

import importlib

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer

from Modules.config_manager import Settings
from Modules.resources_manager import load_favicon
from UI.HomeWindow.home_window_ui import HomeWindowUI
from Modules.log_utils import log 


class HomeWindow(QWidget):
    def __init__(self):
        log("[HOME] __init__ avviato", level="DEBUG")
        super().__init__()
        
        # 1. Caricamento UI
        log("[HOME] Costruzione UI in corso", level="DEBUG")
        self.ui = HomeWindowUI.build()
        
        # 2. Configurazione Widget (Mapping layout dalla UI generata)
        log("[HOME] Applicazione layout e proprietà finestra", level="DEBUG")
        self.setLayout(self.ui.root.layout())
        self.setMinimumSize(self.ui.root.minimumSize())
        self.setWindowTitle(self.ui.root.windowTitle())
        self.setStyleSheet(self.ui.root.styleSheet())

        # 4. Connessione Eventi
        log("[HOME] Collegamento eventi UI", level="DEBUG")
        self._wire_events()
        self.settings = None
        self._set_navigation_enabled(False)
        QTimer.singleShot(0, self._load_settings_deferred)

        # 5. Gestione Avvio Sicuro (Anti-Crash COM)
        # Delay di 500ms per stabilità Windows/Rendering
        QTimer.singleShot(500, self._on_startup_stable)

        log("[HOME] __init__ completato", level="DEBUG")

    def _set_navigation_enabled(self, enabled: bool) -> None:
        self.ui.bt_settings_small.setEnabled(enabled)
        self.ui.bt_race_manager.setEnabled(enabled)
        self.ui.bt_driver_manager.setEnabled(enabled)
        self.ui.bt_circuits.setEnabled(enabled)
        self.ui.bt_grid.setEnabled(enabled)
        self.ui.bt_new_list.setEnabled(enabled)
        self.ui.bt_roadsters.setEnabled(enabled)

    def _load_settings_deferred(self) -> None:
        log("[HOME] Caricamento impostazioni in corso", level="DEBUG")
        self.settings = Settings.load_default()
        load_favicon(root_path=self.settings.root_path)
        self._set_navigation_enabled(True)
        QTimer.singleShot(0, self._warm_up_secondary_modules)
        log("[HOME] Impostazioni caricate")

    def _warm_up_secondary_modules(self) -> None:
        try:
            importlib.import_module("UI.RaceManagerWindow.race_manager_window")
            log("[HOME] Warm-up RaceManagerWindow completato", level="DEBUG")
        except Exception as exc:
            log(f"[HOME] Warm-up RaceManagerWindow fallito: {exc}", level="DEBUG")

    def _on_startup_stable(self):
        """Eseguito quando l'interfaccia è visibile e la COM è pronta."""
        log("[HOME] Interfaccia pronta e stabile")

    def _wire_events(self) -> None:
        self.ui.bt_settings_small.clicked.connect(self.open_settings)
        self.ui.bt_race_manager.clicked.connect(self.open_race_manager)
        self.ui.bt_driver_manager.clicked.connect(self.open_driver_manager)
        self.ui.bt_circuits.clicked.connect(self.open_circuit_manager)
        self.ui.bt_grid.clicked.connect(self.open_grid_preview)
        self.ui.bt_new_list.clicked.connect(self.open_racelist_manager)
        self.ui.bt_roadsters.clicked.connect(self.open_roadster_creator)

    # ======= EVENTI DI SISTEMA =======
    def showEvent(self, event):
        log("[HOME] Finestra in fase di visualizzazione", level="DEBUG")
        return super().showEvent(event)

    def event(self, e):
        t = int(e.type())
        if t in (17, 26): 
            log(f"[HOME] Evento Qt tipo={t}", level="DEBUG")
        return super().event(e)

    # ======= AZIONI BOTTONI (LAZY IMPORTS) =======
    
    def open_settings(self) -> None:
        log("[HOME] Apertura Impostazioni")
        from UI.SettingsWindow.settings_window import SettingsWindow
        dlg = SettingsWindow(self, self.settings)
        # Se SettingsWindow è un QDialog e vuoi che blocchi la home:
        dlg.exec() 
        # Altrimenti se è un QWidget e vuoi massimizzarlo:
        # dlg.showMaximized()
    def open_race_manager(self) -> None:
        log("[HOME] Apertura Gestore Gara")
        from PySide6.QtCore import Qt
        from UI.RaceManagerWindow.race_manager_window import RaceManagerWindow

        # parent=None -> top-level window vera
        self.race_window = RaceManagerWindow(settings=self.settings, parent=None)
        self.race_window.setAttribute(Qt.WA_DeleteOnClose)
        self.race_window.destroyed.connect(self.show)
        self.race_window.setWindowTitle("Race Manager System")
        self.hide()
        self.race_window.showMaximized()
        self.race_window.activateWindow()
        self.race_window.raise_()

    def open_driver_manager(self) -> None:
        log("[HOME] Apertura Gestore Piloti")
        from UI.DriversWindow.drivers_window import DriversWindow
        dlg = DriversWindow(self, self.settings)
        self.hide()
        dlg.exec()
        self.show()

    def open_circuit_manager(self) -> None:
        log("[HOME] Apertura Gestore Circuiti")
        from UI.CircuitsWindow.circuits_window import CircuitsWindow
        dlg = CircuitsWindow(self, self.settings)
        self.hide()
        dlg.exec()
        self.show()

    def open_grid_preview(self) -> None:
        log("[HOME] Apertura Anteprima Griglia")
        from UI.GridWindow.grid_window import GridWindow
        dlg = GridWindow(self, self.settings)
        self.hide()
        dlg.exec()
        self.show()

    def open_racelist_manager(self) -> None:
        log("[HOME] Apertura Gestore Liste Gara")
        from UI.RaceListWindow.racelist_window import RaceListWindow
        dlg = RaceListWindow(self, self.settings)
        self.hide()
        dlg.exec()
        self.show()

    def open_roadster_creator(self) -> None:
        log("[HOME] Apertura Creatore Roadster")
        from UI.RoadsterWindow.roadster_window import RoadsterWindow
        dlg = RoadsterWindow(self, self.settings)
        self.hide()
        dlg.exec()
        self.show()