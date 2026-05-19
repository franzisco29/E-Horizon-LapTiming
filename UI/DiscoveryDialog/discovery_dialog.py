"""
Discovery Dialog per configurazione dispositivi.

In LAPMONITOR mode: Scansione BLE per trovare LapMonitor
In TCP mode: Mostra status dispositivi TCP
"""

import asyncio
import threading
from typing import Optional, List, Dict, Callable

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
    QComboBox
)
from PySide6.QtGui import QFont

from Modules.log_utils import log
from Modules.config_manager import Settings

try:
    from bleak import BleakScanner
except ImportError:
    BleakScanner = None  # type: ignore


class DiscoveryWorker(QObject):
    """Worker per BLE scan async."""
    finished = Signal(list)  # Lista di (mac, name) tuples
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._thread: Optional[threading.Thread] = None

    def start_scan(self) -> None:
        """Avvia BLE scan in thread separato."""
        self._thread = threading.Thread(target=self._run_scan, daemon=True)
        self._thread.start()

    def _run_scan(self) -> None:
        """Esegui BLE scan."""
        try:
            if BleakScanner is None:
                self.error.emit("Bleak non installato. Installa con: pip install bleak")
                return

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                devices = loop.run_until_complete(BleakScanner.discover(timeout=10.0))
                
                # Filtra dispositivi BLE: nome valorizzato e prefisso "Lap".
                results = []
                for device in devices:
                    name = (device.name or "").strip()
                    mac = device.address

                    # I dispositivi target iniziano tutti con "Lap".
                    if name and name.lower().startswith("lap") and mac:
                        results.append((mac, name))
                
                log(f"[Discovery] BLE scan completato: {len(results)} dispositivi filtrati (prefisso 'Lap')")
                self.finished.emit(results)
            finally:
                loop.close()
        
        except Exception as e:
            log(f"[Discovery] Errore scan BLE: {e}", level="ERROR")
            self.error.emit(f"Errore scansione BLE: {e}")


class DiscoveryDialog(QDialog):
    """Dialog per scoperta dispositivi."""

    def __init__(self, parent, settings: Settings, conn_type: int):
        super().__init__(parent)
        self.settings = settings
        self.conn_type = int(conn_type)
        self.selected_mac: Optional[str] = None
        self.selected_tcp_devices: Dict[int, bool] = {}

        self.setWindowTitle("Scoperta Dispositivi")
        self.setMinimumSize(600, 400)
        self.setFont(QFont("Google Sans", 10))

        # UI
        layout = QVBoxLayout(self)

        # Titolo
        if self.conn_type == 2:  # LAPMONITOR
            title_label = QLabel("🔍 Scansione BLE - Ricerca LapMonitor")
            title_label.setFont(QFont("Google Sans", 12, QFont.Bold))
            layout.addWidget(title_label)

            # Descrizione
            desc = QLabel(
                "Ricerca dispositivi LapMonitor via Bluetooth.\n"
                "Seleziona il dispositivo e premi 'Connetti tutto'."
            )
            layout.addWidget(desc)

            # List di dispositivi scoperti
            self.device_list = QListWidget()
            layout.addWidget(QLabel("Dispositivi disponibili:"))
            layout.addWidget(self.device_list)

            # Progress bar
            self.progress = QProgressBar()
            self.progress.setMaximum(0)  # Indeterminate
            self.progress.setVisible(False)
            layout.addWidget(self.progress)

            # Bottoni scan
            button_layout = QHBoxLayout()
            self.scan_btn = QPushButton("▶️ Avvia Scansione")
            self.scan_btn.clicked.connect(self._start_ble_scan)
            button_layout.addWidget(self.scan_btn)
            layout.addLayout(button_layout)

        else:  # TCP mode (conn_type == 1 o 0)
            title_label = QLabel("📡 Configurazione Dispositivi TCP")
            title_label.setFont(QFont("Google Sans", 12, QFont.Bold))
            layout.addWidget(title_label)

            desc = QLabel(
                "Nessuna scoperta automatica in TCP mode.\n"
                "Assicurati che i dispositivi siano connessi manualmente."
            )
            layout.addWidget(desc)

        # Spacer
        layout.addStretch()

        # Bottoni OK/Cancel
        button_box = QHBoxLayout()
        self.ok_btn = QPushButton("✓ Connetti tutto")
        self.ok_btn.clicked.connect(self._on_connect)
        self.cancel_btn = QPushButton("✗ Annulla")
        self.cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(self.ok_btn)
        button_box.addWidget(self.cancel_btn)
        layout.addLayout(button_box)

        # Worker per BLE scan
        self.worker = DiscoveryWorker()
        self.worker.finished.connect(self._on_scan_complete)
        self.worker.error.connect(self._on_scan_error)

        # Auto-disable OK se LAPMONITOR e nessun device selezionato
        self.ok_btn.setEnabled(self.conn_type != 2)

        self._scan_timer: Optional[QTimer] = None

    def _start_ble_scan(self) -> None:
        """Avvia scansione BLE."""
        if self.conn_type != 2:
            return

        log("[Discovery] Avvio scansione BLE...")
        self.device_list.clear()
        self.progress.setVisible(True)
        self.scan_btn.setEnabled(False)
        self.ok_btn.setEnabled(False)

        self.worker.start_scan()

        # Timeout dopo 15 secondi
        self._scan_timer = QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.timeout.connect(self._on_scan_timeout)
        self._scan_timer.start(15000)

    def _on_scan_complete(self, devices: List[tuple[str, str]]) -> None:
        """Callback quando scansione BLE completata."""
        if self._scan_timer:
            self._scan_timer.stop()

        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)

        if not devices:
            QMessageBox.warning(self, "Nessun dispositivo", "Nessun dispositivo BLE trovato.")
            return

        # Popola lista
        self.device_list.clear()
        for mac, name in devices:
            item = QListWidgetItem(f"{name} ({mac})")
            item.setData(Qt.UserRole, mac)
            self.device_list.addItem(item)

        log(f"[Discovery] Scansione BLE completata: {len(devices)} dispositivi")
        self.ok_btn.setEnabled(True)

    def _on_scan_error(self, error_msg: str) -> None:
        """Callback errore BLE scan."""
        if self._scan_timer:
            self._scan_timer.stop()

        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        QMessageBox.critical(self, "Errore Scansione", error_msg)
        log(f"[Discovery] Errore scan: {error_msg}", level="ERROR")

    def _on_scan_timeout(self) -> None:
        """Timeout BLE scan."""
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        # Non interrompiamo lo scan, ma passiamo ai risultati attuali

    def _on_connect(self) -> None:
        """Salva configurazione e chiudi dialog."""
        if self.conn_type == 2:  # LAPMONITOR
            selected_items = self.device_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Selezione richiesta", "Seleziona un dispositivo LapMonitor.")
                return

            item = selected_items[0]
            self.selected_mac = item.data(Qt.UserRole)
            log(f"[Discovery] MAC selezionato: {self.selected_mac}")

            # Salva in settings
            if self.selected_mac:
                self.settings.ble_mac_address = self.selected_mac
                try:
                    self.settings.save()
                    log("[Discovery] Configurazione salvata")
                except Exception as e:
                    log(f"[Discovery] Errore salvataggio: {e}", level="ERROR")
                    QMessageBox.warning(self, "Errore", f"Non è stato possibile salvare: {e}")
                    return

        self.accept()
