from __future__ import annotations

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer

from Modules.config_manager import Settings
from UI.HomeWindow.home_window_ui import HomeWindowUI
from Modules.log_utils import log 


class HomeWindow(QWidget):
    def __init__(self):
        log("HomeWindow.__init__ ENTER")
        super().__init__()
        
        # 1. Caricamento UI
        log("HomeWindow building UI...")
        self.ui = HomeWindowUI.build()
        
        # 2. Configurazione Widget (Mapping layout dalla UI generata)
        log("HomeWindow applying layout props...")
        self.setLayout(self.ui.root.layout())
        self.setMinimumSize(self.ui.root.minimumSize())
        self.setWindowTitle(self.ui.root.windowTitle())
        self.setStyleSheet(self.ui.root.styleSheet())
        
        # 3. Inizializzazione dati (Settings)
        # Usiamo load_default() che gestisce automaticamente path e creazione file
        log("HomeWindow loading settings...")
        self.settings = Settings.load_default() 

        # 4. Connessione Eventi
        log("HomeWindow wiring events...")
        self._wire_events()

        # 5. Gestione Avvio Sicuro (Anti-Crash COM)
        # Delay di 500ms per stabilità Windows/Rendering
        QTimer.singleShot(500, self._on_startup_stable)

        log("HomeWindow.__init__ EXIT")

    def _on_startup_stable(self):
        """Eseguito quando l'interfaccia è visibile e la COM è pronta."""
        log("HomeWindow stabile e pronta. Event loop operativo.")

    def _wire_events(self) -> None:
        self.ui.bt_settings_small.clicked.connect(self.open_settings)
        self.ui.bt_race_manager.clicked.connect(self.open_race_manager)
        self.ui.bt_driver_manager.clicked.connect(self.open_driver_manager)
        self.ui.bt_grid.clicked.connect(self.open_grid_preview)
        self.ui.bt_new_list.clicked.connect(self.open_racelist_manager)
        self.ui.bt_roadsters.clicked.connect(self.open_roadster_creator)

    # ======= EVENTI DI SISTEMA =======
    def showEvent(self, event):
        log("HomeWindow.showEvent - Finestra in fase di visualizzazione")
        return super().showEvent(event)

    def event(self, e):
        t = int(e.type())
        if t in (17, 26): 
            log(f"HomeWindow.event type={t}")
        return super().event(e)

    # ======= AZIONI BOTTONI (LAZY IMPORTS) =======
    
    def open_settings(self) -> None:
        log("HomeWindow.open_settings CLICK")
        from UI.SettingsWindow.settings_window import SettingsWindow
        dlg = SettingsWindow(self, self.settings)
        # Se SettingsWindow è un QDialog e vuoi che blocchi la home:
        dlg.exec() 
        # Altrimenti se è un QWidget e vuoi massimizzarlo:
        # dlg.showMaximized()
    def open_race_manager(self) -> None:
        log("HomeWindow.open_race_manager CLICK")
        from UI.RaceManagerWindow.race_manager_window import RaceManagerWindow

        # parent=None -> top-level window vera
        self.race_window = RaceManagerWindow(settings=self.settings, parent=None)
        self.race_window.setWindowTitle("Race Manager System")
        self.race_window.showMaximized()
        self.race_window.activateWindow()
        self.race_window.raise_()

    def open_driver_manager(self) -> None:
        log("HomeWindow.open_driver_manager CLICK")
        from UI.DriversWindow.drivers_window import DriversWindow
        dlg = DriversWindow(self, self.settings)
        dlg.exec()

    def open_grid_preview(self) -> None:
        log("HomeWindow.open_grid_preview CLICK")
        from UI.GridWindow.grid_window import GridWindow
        dlg = GridWindow(self, self.settings)
        dlg.exec()

    def open_racelist_manager(self) -> None:
        log("HomeWindow.open_racelist_manager CLICK")
        from UI.RaceListWindow.racelist_window import RaceListWindow
        dlg = RaceListWindow(self, self.settings)
        dlg.exec()

    def open_roadster_creator(self) -> None:
        log("HomeWindow.open_roadster_creator CLICK")
        from UI.RoadsterWindow.roadster_window import RoadsterWindow
        dlg = RoadsterWindow(self, self.settings)
        dlg.exec()