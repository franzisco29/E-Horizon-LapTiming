from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QFileDialog

from Modules.config_manager import Settings
from Modules.net import get_local_ipv4
from UI.SettingsWindow.settings_window_ui import SettingsWindowUI


class SettingsWindow(QDialog):
    def __init__(self, parent, settings: Settings):
        super().__init__(parent)
        # Imposta font esplicito con pointSize > 0 prima di costruire la UI.
        # La home usa font-size in px → pointSize()=-1; senza questo Qt stampa
        # "QFont::setPointSize: Point size <= 0 (-1)" quando applica pt nel stylesheet.
        self.setFont(QFont("Google Sans", 10))
        self.settings = settings
        self._monitor_initial = int(settings.monitor_out)
        self._path_initial = str(settings.root_path)
        self._path_changed = False

        self.ui = SettingsWindowUI(self)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.addWidget(self.ui)

        self.setWindowTitle(self.ui.windowTitle())
        self.setMinimumSize(self.ui.minimumSize())

        self._wire()
        self._load_to_ui()
        self._apply_permissions()


    # -------------------------
    # Wire events
    # -------------------------
    def _wire(self) -> None:
        r = self.ui.refs
        r.cancel_btn.clicked.connect(self._cancel)
        r.save_btn.clicked.connect(self._save)

        r.live_check.stateChanged.connect(self._live_toggle)
        r.live_check.stateChanged.connect(self._refresh_summary)
        r.manual_start_check.stateChanged.connect(self._refresh_summary)
        r.tv_tower_check.stateChanged.connect(lambda _s: None)
        r.conn_type_combo.currentIndexChanged.connect(self._conn_type_changed)
        r.conn_type_combo.currentIndexChanged.connect(self._refresh_summary)
        r.debug_check.stateChanged.connect(lambda _s: None)

        r.browse_btn.clicked.connect(self._browse_folder)

    # -------------------------
    # Populate UI
    # -------------------------
    def _load_to_ui(self) -> None:
        r = self.ui.refs

        r.debug_check.setChecked(bool(self.settings.debug))
        r.live_check.setChecked(bool(self.settings.live_enabled))
        r.tv_tower_check.setChecked(bool(self.settings.tv_enabled))
        r.manual_start_check.setChecked(bool(getattr(self.settings, "manual_start", True)))
        r.heartbeat_interval_edit.setText(str(int(getattr(self.settings, "heartbeat_interval_s", 5))))
        r.heartbeat_max_missed_edit.setText(str(int(getattr(self.settings, "heartbeat_max_missed", 3))))

        # Monitor list
        r.monitor_combo.clear()
        screens = QGuiApplication.screens()
        for i, s in enumerate(screens):
            geo = s.geometry()
            r.monitor_combo.addItem(f"Monitor {i}: {s.name()} - {geo.width()}x{geo.height()}")
        try:
            r.monitor_combo.setCurrentIndex(int(self.settings.monitor_out))
        except Exception:
            r.monitor_combo.setCurrentIndex(0)

        r.conn_type_combo.setCurrentIndex(int(self.settings.connection_type))
        r.debounce_edit.setText(str(int(self.settings.debounce_ms)))
        r.tcp_ip_value_label.setText(get_local_ipv4())

        r.tcp_port_edit.setText(str(int(self.settings.tcp_port)))

        flags = self.settings.devices.device_available_flags(expected_len=6)
        for i, cb in enumerate(r.dev_checks):
            cb.setChecked(bool(flags[i]))

        r.live_ip_edit.setText(str(self.settings.live_ip))
        r.live_port_edit.setText(str(int(self.settings.live_port)))

        r.root_path_edit.setText(str(self.settings.root_path))

        # enable/disable parts
        self._apply_feature_availability()
        self._live_toggle()
        self._conn_type_changed()
        self._refresh_summary()

    def _apply_permissions(self) -> None:
        # VB: admin=0 -> disabilita quasi tutto
        r = self.ui.refs
        admin = int(self.settings.admin)

        if admin == 0:
            r.tcp_box.setEnabled(False)
            r.live_check.setEnabled(False)
            r.debug_check.setEnabled(False)
            r.conn_type_combo.setEnabled(False)
            r.debounce_edit.setEnabled(False)
            r.manual_start_check.setEnabled(False)
            r.heartbeat_interval_edit.setEnabled(False)
            r.heartbeat_max_missed_edit.setEnabled(False)
            r.root_path_edit.setEnabled(False)
            r.browse_btn.setEnabled(False)
            r.tv_tower_check.setEnabled(False)

    def _apply_feature_availability(self) -> None:
        r = self.ui.refs

        r.tv_tower_check.setEnabled(False)
        r.tv_tower_check.setToolTip("Opzione non disponibile: Tv Tower non viene usata dall'app.")

    # -------------------------
    # UI reactions
    # -------------------------
    def _live_toggle(self) -> None:
        r = self.ui.refs
        on = r.live_check.isChecked()

        r.live_box.setEnabled(on)
        r.live_box.setToolTip(
                "" if on else "Attiva 'Live Timing' per modificare IP e porta."
            )

    def _conn_type_changed(self) -> None:
        r = self.ui.refs
        admin = int(self.settings.admin)
        conn_index = r.conn_type_combo.currentIndex()

        is_tcp = conn_index == 1 and admin != 0
        is_lapmonitor = conn_index == 2

        # In LAPMONITOR, disabilita D1-D4 (indici 1-4 nei checkbox)
        for i, cb in enumerate(r.dev_checks):
            if i in [1, 2, 3, 4]:  # D1, D2, D3, D4
                cb.setEnabled(not is_lapmonitor and admin != 0)
                if is_lapmonitor:
                    cb.setChecked(False)
            else:
                cb.setEnabled(admin != 0)

        r.tcp_port_edit.setEnabled(is_tcp)
        r.tcp_port_edit.setToolTip(
            "" if is_tcp else "Abilita 'Comunicazione: TCP' per modificare la porta TCP."
        )

        r.heartbeat_interval_edit.setEnabled(is_tcp)
        r.heartbeat_interval_edit.setToolTip(
            "" if is_tcp else "Abilita 'Comunicazione: TCP' per modificare l'intervallo heartbeat."
        )
        r.heartbeat_max_missed_edit.setEnabled(is_tcp)
        r.heartbeat_max_missed_edit.setToolTip(
            "" if is_tcp else "Abilita 'Comunicazione: TCP' per modificare i heartbeat mancati massimi."
        )

    def _refresh_summary(self) -> None:
        r = self.ui.refs

        conn_map = {
            0: "NONE",
            1: "TCP",
            2: "LAPMONITOR",
            3: "SERIAL",
        }

        conn_mode = conn_map.get(int(r.conn_type_combo.currentIndex()), "UNKNOWN")
        start_mode = "Manuale" if r.manual_start_check.isChecked() else "Automatico"
        live_mode = "Attivo" if r.live_check.isChecked() else "Disattivo"
        profile_mode = "Admin" if int(self.settings.admin) != 0 else "User"

        r.summary_conn_value.setText(conn_mode)
        r.summary_start_value.setText(start_mode)
        r.summary_live_value.setText(live_mode)
        r.summary_profile_value.setText(profile_mode)


    # -------------------------
    # Browse folder
    # -------------------------
    def _browse_folder(self) -> None:
        r = self.ui.refs
        current = Path(r.root_path_edit.text().strip()) if r.root_path_edit.text().strip() else Path.cwd()
        folder = QFileDialog.getExistingDirectory(self, "Seleziona la nuova cartella per i dati", str(current))
        if folder:
            old = r.root_path_edit.text()
            r.root_path_edit.setText(str(Path(folder)))
            self._path_changed = (r.root_path_edit.text() != old)

    # -------------------------
    # Save / Cancel
    # -------------------------
    def _cancel(self) -> None:
        resp = QMessageBox.question(
            self,
            "Annulla",
            "Sei sicuro di voler annullare le modifiche?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self.reject()

    def _save(self) -> None:
        r = self.ui.refs

        # ---- read from ui, validate
        try:
            debounce = int(r.debounce_edit.text().strip())
        except Exception:
            QMessageBox.warning(self, "Valore non valido", "DeBounce Time deve essere un numero (ms).")
            return

        try:
            tcp_port = int(r.tcp_port_edit.text().strip())
        except Exception:
            QMessageBox.warning(self, "Valore non valido", "TCP Port deve essere un numero.")
            return

        try:
            live_port = int(r.live_port_edit.text().strip())
        except Exception:
            QMessageBox.warning(self, "Valore non valido", "LIVE Port deve essere un numero.")
            return

        try:
            heartbeat_interval = int(r.heartbeat_interval_edit.text().strip())
        except Exception:
            QMessageBox.warning(self, "Valore non valido", "Intervallo heartbeat deve essere un numero.")
            return

        try:
            heartbeat_missed = int(r.heartbeat_max_missed_edit.text().strip())
        except Exception:
            QMessageBox.warning(self, "Valore non valido", "Heartbeat mancati massimi deve essere un numero.")
            return

        # ---- write to settings
        self.settings.debug = bool(r.debug_check.isChecked())
        self.settings.live_enabled = bool(r.live_check.isChecked())
        self.settings.connection_type = int(r.conn_type_combo.currentIndex())
        self.settings.debounce_ms = debounce
        self.settings.manual_start = bool(r.manual_start_check.isChecked())
        self.settings.tcp_port = tcp_port
        self.settings.monitor_out = int(r.monitor_combo.currentIndex())
        self.settings.heartbeat_interval_s = heartbeat_interval
        self.settings.heartbeat_max_missed = heartbeat_missed

        flags = [cb.isChecked() for cb in r.dev_checks]
        self.settings.devices.set_device_available_flags(flags)

        self.settings.live_ip = r.live_ip_edit.text().strip() or "127.0.0.1"
        self.settings.live_port = live_port
        self.settings.tv_enabled = bool(r.tv_tower_check.isChecked())

        new_root = r.root_path_edit.text().strip()
        if new_root:
            self.settings.root_path = new_root

        # persist yaml
        self.settings.save()

        # monitor restart prompt
        monitor_changed = (self._monitor_initial != int(self.settings.monitor_out))
        if monitor_changed:
            resp = QMessageBox.question(
                self,
                "Riavvio richiesto",
                "Le modifiche richiedono un riavvio. Riavviare ora?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp == QMessageBox.Yes:
                # qui tu hai già una funzione RestartApplication in VB
                # in python: puoi emettere un signal e farlo dal main, oppure semplice close.
                self.accept()
                return
            else:
                self.accept()
                return

        self.accept()
