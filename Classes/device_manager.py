from __future__ import annotations

import re
import socket
import struct
import threading
import time
from datetime import datetime
from enum import IntEnum
from typing import Callable, Dict, List, Optional, Sequence, Union, TYPE_CHECKING

from Classes.device import Device
from Modules.device_commands import DeviceCommand
from Modules.log_utils import log  # logger tuo
from PySide6.QtCore import QObject, Signal

try:
    from lap_monitor import LapMonitor
except ImportError:
    LapMonitor = None  # type: ignore


class ConnectionTypes(IntEnum):
    NONE = 0
    TCP = 1
    LAPMONITOR = 2
    SERIAL = 3


class DeviceManager(QObject):
    # Qt signal emitted when device list changes
    devicesChanged = Signal()
    class DevicesIDs(IntEnum):
        Central = 0
        S1 = 1
        S2 = 2
        PitIn = 3
        PitOut = 4
        Sem = 5
        AttZoneIn = 6
        AttZoneOut = 7
        RacePanel = 8

    class DeviceNames:
        LAP_DONE = "Lap Done"
        S1 = "Sect. 1"
        S2 = "Sect. 2"
        PIN = "Pit In"
        POUT = "Pit Out"
        SEM = "Semaforo"
        ATIN = "Att. Zone in"
        ATOUT = "Att. Zone Out"
        RACEPANEL = "Race Panel"

    """
    VB DeviceManager -> Python

    - Server TCP che accetta fino a MAX_DEVICES
    - Handshake: invia CONN_CMD, aspetta risposta "C:D1IPx.x.x.x"
    - Per ogni device: thread di ricezione line-based

    Callback:
        on_transponder_received(device_id: str, transponder_id: int)      # legacy ("D0")
        on_transponder_received_index(device: int, transponder_id: int)  # NEW (0..N)
        on_log(message: str)
    """

    DEVICE_NAMES: Sequence[str] = (
        DeviceNames.LAP_DONE,
        DeviceNames.S1,
        DeviceNames.S2,
        DeviceNames.PIN,
        DeviceNames.POUT,
        DeviceNames.SEM,
        DeviceNames.ATIN,
        DeviceNames.ATOUT,
        DeviceNames.RACEPANEL,
    )
    MAX_DEVICES: int = len(DEVICE_NAMES)
    # Device accettati sempre alla connessione, indipendentemente da active_flags
    _ALWAYS_ACCEPTED_IDS: frozenset[int] = frozenset({DevicesIDs.RacePanel})
    _VALID_TCP_COMMANDS: set[str] = {c.value for c in DeviceCommand}
    _TCP_COMMAND_ALIASES: dict[str, str] = {
        "VSC": DeviceCommand.VIRTUAL_SC_CMD.value,
    }
    _SPECIAL_TCP_COMMANDS: set[str] = {"STP"}
    _HANDSHAKE_RESPONSE_TIMEOUT_S: float = 3.0
    _HEARTBEAT_INTERVAL_S: float = 5.0
    _HEARTBEAT_TIMEOUT_S: float = 2.0
    _HEARTBEAT_MAX_MISSED: int = 3

    # Simulazione transponder (legacy: (number, device))
    _transponder_simulated_listeners: List[Callable[[int, int], None]] = []
    # Simulazione transponder (NEW: (device, number))
    _transponder_simulated_index_listeners: List[Callable[[int, int], None]] = []

    @classmethod
    def add_transponder_simulated_listener(cls, fn: Callable[[int, int], None]) -> None:
        cls._transponder_simulated_listeners.append(fn)

    @classmethod
    def add_transponder_simulated_index_listener(cls, fn: Callable[[int, int], None]) -> None:
        cls._transponder_simulated_index_listeners.append(fn)

    @classmethod
    def simulate_transponder(cls, number: int, device: int) -> None:
        # legacy listeners: (number, device)
        for fn in list(cls._transponder_simulated_listeners):
            try:
                fn(int(number), int(device))
            except Exception as ex:
                log(f"[DEVICE_MGR] Errore simulazione transponder: {ex}", level="ERROR")

        # index listeners: (device, number)
        for fn in list(cls._transponder_simulated_index_listeners):
            try:
                fn(int(device), int(number))
            except Exception as ex:
                log(f"[DEVICE_MGR] Errore simulazione transponder (index): {ex}", level="ERROR")

    def __init__(
        self,
        ip: str,
        port: int = 20777,
        conn_type: Union[int, ConnectionTypes] = ConnectionTypes.TCP,
        active_flags: Optional[Sequence[bool]] = None,
        debug_log: bool = False,
        handshake_delay_ms: int = 250,
        heartbeat_interval_s: Optional[float] = None,
        heartbeat_timeout_s: Optional[float] = None,
        heartbeat_max_missed: Optional[int] = None,
        # debug: timeouts per evitare blocchi "muti"; None -> no timeout
        accept_timeout_s: Optional[float] = None,
        client_socket_timeout_s: Optional[float] = None,
        ble_mac_address: str = "",
        ble_min_lap_s: Optional[float] = None,
    ) -> None:
        super().__init__()
        self.ip = ip
        self.port = port
        self.conn_type = ConnectionTypes(int(conn_type))
        self.debug_log = bool(debug_log)

        # Override heartbeat tuning (per-instance). Methods read these via self.*.
        if heartbeat_interval_s is not None:
            try:
                self._HEARTBEAT_INTERVAL_S = max(0.1, float(heartbeat_interval_s))
            except Exception:
                pass
        if heartbeat_timeout_s is not None:
            try:
                self._HEARTBEAT_TIMEOUT_S = max(0.1, float(heartbeat_timeout_s))
            except Exception:
                pass
        if heartbeat_max_missed is not None:
            try:
                self._HEARTBEAT_MAX_MISSED = max(1, int(heartbeat_max_missed))
            except Exception:
                pass

        # flags: se ne arrivano meno di MAX_DEVICES, le mancanti diventano False
        if active_flags is None:
            self.active_flags = [True] * self.MAX_DEVICES
        else:
            tmp = list(active_flags)
            if len(tmp) < self.MAX_DEVICES:
                tmp.extend([False] * (self.MAX_DEVICES - len(tmp)))
            self.active_flags = tmp[: self.MAX_DEVICES]

        self.sectors_on: bool = False
        self.pit_on: bool = False
        self._last_required_devices_connected_state: Optional[tuple[bool, Optional[str]]] = None

        self._devices: Dict[str, Device] = {}
        self._lock = threading.RLock()

        self._server_sock: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop_evt: threading.Event = threading.Event()
        self._is_running: bool = False

        # BLE gateway (LAPMONITOR mode)
        self._ble_monitor: Optional[object] = None  # type: LapMonitor
        self._ble_connected: bool = False
        self._ble_mac_address: str = ""

        # callbacks
        self.on_transponder_received: Optional[Callable[[str, int], None]] = None
        self.on_transponder_received_index: Optional[Callable[[int, int], None]] = None  # NEW
        self.on_command_received: Optional[Callable[[str, str], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_device_disconnected: Optional[Callable[[str, str], None]] = None
        # called when device list changes (connect / disconnect / clear)
        self.on_devices_changed: Optional[Callable[[], None]] = None

        self._handshake_delay_s = max(0.0, handshake_delay_ms / 1000.0)
        self._accept_timeout_s = None if accept_timeout_s is None else float(accept_timeout_s)
        self._client_socket_timeout_s = None if client_socket_timeout_s is None else float(client_socket_timeout_s)

        # Istanziazione BLE gateway per LAPMONITOR
        self._ble_mac_address = str(ble_mac_address).strip()
        if ble_min_lap_s is None:
            self._ble_min_lap_s = 5.0
        else:
            try:
                self._ble_min_lap_s = max(0.0, float(ble_min_lap_s))
            except Exception:
                self._ble_min_lap_s = 5.0
        if self.conn_type == ConnectionTypes.LAPMONITOR and self._ble_mac_address:
            if LapMonitor is None:
                self._log("INIT", "WARN: LapMonitor non disponibile (Bleak non installato)")
            else:
                try:
                    self._ble_monitor = LapMonitor(
                        address=self._ble_mac_address,
                        min_lap_s=self._ble_min_lap_s,
                        debug=self.debug_log
                    )
                    self._ble_monitor.on_lap = self._on_ble_lap
                    self._ble_monitor.on_status = self._on_ble_status
                    self._log("INIT", f"LapMonitor BLE gateway creato per {self._ble_mac_address} (min_lap_s={self._ble_min_lap_s:.3f})")
                except Exception as ex:
                    self._log("INIT", f"ERRORE: non è stato possibile creare LapMonitor: {ex}")

        self._log("INIT", f"DeviceManager creato — ip={ip} port={port} conn_type={self.conn_type.name}")
        self._log("INIT", f"MAX_DEVICES={self.MAX_DEVICES} DEVICE_NAMES={list(self.DEVICE_NAMES)}")
        self._log("INIT", f"active_flags={self.active_flags}")
        self._log("INIT", f"handshake_delay_s={self._handshake_delay_s}")
        self._log("INIT", f"handshake_response_timeout_s={self._HANDSHAKE_RESPONSE_TIMEOUT_S}")
        self._log("INIT", f"heartbeat interval={self._HEARTBEAT_INTERVAL_S}s timeout={self._HEARTBEAT_TIMEOUT_S}s max_missed={self._HEARTBEAT_MAX_MISSED}")
        self._log("INIT", f"accept_timeout_s={self._accept_timeout_s} client_socket_timeout_s={self._client_socket_timeout_s} (None = nessun timeout)")

        if self.conn_type in (ConnectionTypes.TCP, ConnectionTypes.LAPMONITOR):
            self.start()

    # -------------------------
    # Lifecycle
    # -------------------------
    def start(self) -> None:
        self._log("START", "start() chiamato")
        self._log("START", f"Config: ip={self.ip}, port={self.port}, conn_type={self.conn_type.name}")

        if self.conn_type == ConnectionTypes.NONE:
            self._log("START", "ConnectionTypes.NONE → server non avviato")
            return

        if self._is_running:
            self._log("START", "Server già in esecuzione")
            return

        # Avvia BLE monitor se LAPMONITOR
        if self.conn_type == ConnectionTypes.LAPMONITOR:
            if self._ble_monitor:
                try:
                    self._ble_monitor.start()
                    self._log("START", "BLE monitor avviato")
                except Exception as ex:
                    self._log("START", f"ERRORE avvio BLE monitor: {ex}")
            else:
                self._log("START", "WARN: BLE monitor non disponibile")

        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            self._log("START", f"Server in ascolto su 0.0.0.0:{self.port} (tutte le interfacce)")
            self._log("START", f"Connetti a: {self.ip}:{self.port} dal dispositivo esterno")
            self._log("START", f"Binding su 0.0.0.0:{self.port}")
            self._server_sock.bind(("0.0.0.0", self.port))

            self._server_sock.listen(20)
            if self._accept_timeout_s is not None:
                self._server_sock.settimeout(self._accept_timeout_s)

            self._is_running = True
            self._log("START", f"Server in ascolto sulla porta {self.port}")

            self._accept_thread = threading.Thread(
                target=self._accept_clients_loop,
                daemon=True,
                name="DM-AcceptLoop",
            )
            self._accept_thread.start()
            self._log("START", "Thread accept loop avviato")
            self._start_heartbeat_loop()

        except Exception as ex:
            self._log("ERROR", f"start() fallito: {ex}")

    def disconnect_all(self) -> None:
        self._log("STOP", "disconnect_all() chiamato")

        self._is_running = False
        self._stop_heartbeat_loop()

        # Ferma BLE monitor se LAPMONITOR
        if self.conn_type == ConnectionTypes.LAPMONITOR and self._ble_monitor:
            try:
                self._ble_monitor.stop()
                self._log("STOP", "BLE monitor fermato")
            except Exception as ex:
                self._log("STOP", f"Errore fermo BLE monitor: {ex}")

        with self._lock:
            self._log("STOP", f"Chiusura di {len(self._devices)} dispositivo/i")
            for dev in list(self._devices.values()):
                try:
                    self._log("STOP", f"{dev.device_id}: invio DSCN")
                    dev.send_line(DeviceCommand.DSCN.value)
                except Exception as ex:
                    self._log("STOP", f"{dev.device_id}: errore invio DSCN: {ex}")

                try:
                    self._log("STOP", f"{dev.device_id}: close()")
                    dev.close()
                except Exception as ex:
                    self._log("STOP", f"{dev.device_id}: errore chiusura: {ex}")

            self._devices.clear()
            if self.on_devices_changed:
                try:
                    self.on_devices_changed()
                except Exception as ex:
                    self._log("CALLBACK", f"Errore callback on_devices_changed (clear): {ex}")
            try:
                self.devicesChanged.emit()
            except Exception:
                pass

        if self._server_sock is not None:
            try:
                self._log("STOP", "Chiusura server socket")
                try:
                    # SO_LINGER con timeout 0 forza chiusura immediata con RST, evitando TIME_WAIT
                    self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                except Exception:
                    pass
                try:
                    # Provare a shutdown per sbloccare eventuali accept() in corso
                    self._server_sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self._server_sock.close()
                    self._log("STOP", "Server socket chiuso")
                except Exception as ex:
                    self._log("STOP", f"Errore chiusura server socket: {ex}")
                # Assicuriamoci che il thread di accept termini
                try:
                    if self._accept_thread and self._accept_thread.is_alive():
                        self._log("STOP", "Joining accept thread...")
                        self._accept_thread.join(timeout=2.0)
                        self._log("STOP", "Accept thread terminato")
                except Exception:
                    pass
            except Exception as ex:
                self._log("STOP", f"Errore chiusura server socket: {ex}")
            finally:
                self._server_sock = None
                self._accept_thread = None

    # -------------------------
    # Accept / handshake
    # -------------------------
    def _accept_clients_loop(self) -> None:
        if self._server_sock is None:
            self._log("ACCEPT", "Server socket None → uscita accept loop")
            return

        self._log("ACCEPT", "Accept loop avviato")

        while self._is_running:
            client_sock: Optional[socket.socket] = None
            rfile = None
            wfile = None
            try:
                client_sock, addr = self._server_sock.accept()

                self._log("ACCEPT", f"Client connesso da {addr}")

                # timeout per evitare blocchi su recv/readline
                if self._client_socket_timeout_s is not None:
                    client_sock.settimeout(self._client_socket_timeout_s)

                rfile = client_sock.makefile("r", encoding="ascii", newline="\n")
                wfile = client_sock.makefile("w", encoding="ascii", newline="\n")

                # Handshake: invia "C"
                wfile.write(f"{DeviceCommand.CONN.value}\n")
                wfile.flush()
                self._log("HANDSHAKE", f"Handshake inviato '{DeviceCommand.CONN.value}'")

                time.sleep(self._handshake_delay_s)

                self._log("HANDSHAKE", "Lettura risposta handshake (readline)...")
                client_sock.settimeout(self._HANDSHAKE_RESPONSE_TIMEOUT_S)
                response = rfile.readline()
                response = response.strip() if response else ""
                self._log("HANDSHAKE", f"Risposta='{response}'")

                if self._client_socket_timeout_s is not None:
                    client_sock.settimeout(self._client_socket_timeout_s)
                else:
                    client_sock.settimeout(None)

                if not (response.startswith(f"{DeviceCommand.CONN.value}:") or response.startswith("C:")):
                    self._log("HANDSHAKE", "Handshake non valido. Chiusura client.")
                    try:
                        client_sock.close()
                    except Exception as ex:
                        self._log("HANDSHAKE", f"Errore chiusura client (handshake non valido): {ex}")
                    continue

                payload = response.split(":", 1)[1]
                device_id, device_ip = self._extract_device_id_and_ip(payload)
                self._log("HANDSHAKE", f"Payload='{payload}' → device_id={device_id} ip={device_ip}")

                with self._lock:
                    if device_id in self._devices:
                        self._log("HANDSHAKE", f"{device_id} già connesso → connessione rifiutata")
                        try:
                            client_sock.close()
                        except Exception as ex:
                            self._log("HANDSHAKE", f"Errore chiusura client (device duplicato): {ex}")
                        continue

                    dev = Device(
                        device_id=device_id,
                        ip=device_ip,
                        sock=client_sock,
                        _rfile=rfile,
                        _wfile=wfile,
                    )
                    self._devices[device_id] = dev

                # notify listeners that device list changed (callback + Qt signal)
                if self.on_devices_changed:
                    try:
                        self.on_devices_changed()
                    except Exception as ex:
                        self._log("CALLBACK", f"Errore callback on_devices_changed: {ex}")
                try:
                    # emit Qt signal (thread-safe delivery to UI thread)
                    self.devicesChanged.emit()
                except Exception:
                    pass
                self._log("ACCEPT", f"Dispositivo {device_id} registrato")

                t = threading.Thread(
                    target=self._receive_loop,
                    args=(dev,),
                    daemon=True,
                    name=f"DM-RX-{device_id}",
                )
                t.start()
                self._log("ACCEPT", f"Thread RX avviato per {device_id}")

            except socket.timeout:
                # timeout in accept() when server timeout is enabled
                if client_sock is None and self._accept_timeout_s is not None:
                    continue
                # timeout during handshake response read
                if client_sock is not None:
                    self._log("HANDSHAKE", "Timeout risposta handshake. Chiusura client.")
                    self._safe_close_handshake_client(client_sock, rfile, wfile)
                    continue
            except OSError as ex:
                server_stopping = not self._is_running or self._server_sock is None
                if server_stopping:
                    self._log("ACCEPT", f"OSError durante l'arresto: {ex}")
                    break

                self._log("ACCEPT", f"OSError client/socket durante accept o handshake: {ex}")
                self._safe_close_handshake_client(client_sock, rfile, wfile)
                continue
            except Exception as ex:
                self._log("ACCEPT", f"Errore accept/handshake client: {ex}")
                self._safe_close_handshake_client(client_sock, rfile, wfile)

        self._log("ACCEPT", "Accept loop terminato")

    def _safe_close_handshake_client(
        self,
        client_sock: Optional[socket.socket],
        rfile,
        wfile,
    ) -> None:
        for stream in (rfile, wfile):
            if stream is None:
                continue
            try:
                stream.close()
            except Exception:
                pass

        if client_sock is not None:
            try:
                client_sock.close()
            except Exception:
                pass

    def _start_heartbeat_loop(self) -> None:
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return

        self._heartbeat_stop_evt.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="DM-HeartbeatLoop",
        )
        self._heartbeat_thread.start()
        self._log("START", "Thread heartbeat loop avviato")

    def _stop_heartbeat_loop(self) -> None:
        self._heartbeat_stop_evt.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.5)
        self._heartbeat_thread = None

    def _heartbeat_loop(self) -> None:
        self._log("HEARTBEAT", "Heartbeat loop avviato")

        while self._is_running and not self._heartbeat_stop_evt.is_set():
            wait_s = self._HEARTBEAT_INTERVAL_S
            with self._lock:
                deadlines = [
                    dev.heartbeat_deadline_monotonic
                    for dev in self._devices.values()
                    if dev.heartbeat_waiting and dev.heartbeat_deadline_monotonic is not None
                ]
            if deadlines:
                earliest_deadline = min(deadlines)
                wait_s = max(0.0, min(wait_s, earliest_deadline - time.monotonic()))

            if self._heartbeat_stop_evt.wait(wait_s):
                break

            now = time.monotonic()
            to_ping: List[Device] = []
            to_disconnect: List[tuple[str, str]] = []

            with self._lock:
                for dev_id, dev in list(self._devices.items()):
                    if dev.heartbeat_waiting and dev.heartbeat_deadline_monotonic is not None and now >= dev.heartbeat_deadline_monotonic:
                        dev.heartbeat_waiting = False
                        dev.heartbeat_deadline_monotonic = None
                        dev.heartbeat_missed_count += 1
                        self._log(
                            "HEARTBEAT",
                            f"{dev_id}: heartbeat mancato ({dev.heartbeat_missed_count}/{self._HEARTBEAT_MAX_MISSED})",
                        )
                        if dev.heartbeat_missed_count >= self._HEARTBEAT_MAX_MISSED:
                            reason = f"timeout heartbeat ({self._HEARTBEAT_MAX_MISSED} mancati consecutivi)"
                            to_disconnect.append((dev_id, reason))
                            # Notify UI immediately (while still holding lock)
                            if self.on_device_disconnected:
                                try:
                                    self.on_device_disconnected(dev_id, reason)
                                except Exception as ex:
                                    self._log("CALLBACK", f"Errore callback on_device_disconnected (immediate): {ex}")
                            continue

                    if not dev.heartbeat_waiting:
                        dev.heartbeat_waiting = True
                        dev.heartbeat_deadline_monotonic = now + self._HEARTBEAT_TIMEOUT_S
                        to_ping.append(dev)

            for dev in to_ping:
                dev.send_line(DeviceCommand.STATUS_CMD.value)
                self._log("HEARTBEAT", f"{dev.device_id} <- '{DeviceCommand.STATUS_CMD.value}'")

            for dev_id, reason in to_disconnect:
                self._disconnect_device(dev_id, reason=reason, emit_alert=True)

        self._log("HEARTBEAT", "Heartbeat loop terminato")

    def _disconnect_device(self, device_id: str, reason: str, emit_alert: bool = False) -> bool:
        with self._lock:
            dev = self._devices.pop(device_id, None)

        if dev is None:
            return False

        device_label = self._device_label(device_id)
        
        try:
            dev.close()
        except Exception as ex:
            self._log("DISCONNECT", f"{device_label}: errore chiusura socket: {ex}")

        self._log("DISCONNECT", f"{device_label}: disconnesso ({reason})")

        if emit_alert and self.on_device_disconnected:
            try:
                self.on_device_disconnected(device_id, reason)
            except Exception as ex:
                self._log("CALLBACK", f"Errore callback on_device_disconnected: {ex}")

        if self.on_devices_changed:
            try:
                self.on_devices_changed()
            except Exception as ex:
                self._log("CALLBACK", f"Errore callback on_devices_changed (remove): {ex}")

        try:
            self.devicesChanged.emit()
        except Exception as ex:
            self._log("CALLBACK", f"Errore emitting devicesChanged: {ex}")

        return True

    # -------------------------
    # Receive loop
    # -------------------------
    def _receive_loop(self, dev: Device) -> None:
        self._log("RXLOOP", f"RX loop avviato per {dev.device_id}")

        try:
            while self._is_running:
                self._log("RXLOOP", f"{dev.device_id}: attesa read_line()")
                line = dev.read_line()

                if line is None:
                    self._log("RXLOOP", f"{dev.device_id}: read_line() → None (disconnessione)")
                    break

                raw = line
                line = line.strip()
                if not line:
                    self._log("RX", f"{dev.device_id}: riga vuota ignorata (raw={raw!r})")
                    continue

                self._log("RX", f"{dev.device_id} -> {line}")

                if line == "S:OK":
                    with self._lock:
                        same_dev = self._devices.get(dev.device_id) is dev
                        if same_dev:
                            dev.last_status_response = datetime.now()
                            dev.heartbeat_missed_count = 0
                            dev.heartbeat_waiting = False
                            dev.heartbeat_deadline_monotonic = None
                    self._log("HEARTBEAT", f"{dev.device_id}: heartbeat OK")
                    continue

                if line.startswith("P:"):
                    m = re.match(r"^P:D(\d+)T(\d+)$", line)
                    if not m:
                        self._log("PARSER", f"{dev.device_id}: formato P non valido: '{line}'")
                        continue

                    dev_n = int(m.group(1))
                    transponder = int(m.group(2))
                    device_id = f"D{dev_n}"

                    self._log("PARSER", f"P ricevuto: device_id={device_id} transponder={transponder}")

                    # legacy callback: ("D0", 22)
                    if self.on_transponder_received:
                        try:
                            #self._log("CALLBACK", f"Calling on_transponder_received({device_id}, {transponder})")
                            self.on_transponder_received(device_id, transponder)
                            #self._log("CALLBACK", "Callback OK")
                        except Exception as ex:
                            self._log("CALLBACK", f"Errore callback on_transponder_received: {ex}")

                    # NEW callback: (0, 22)
                    if self.on_transponder_received_index:
                        try:
                            self._log("CALLBACK", f"Chiamata on_transponder_received_index({dev_n}, {transponder})")
                            self.on_transponder_received_index(int(dev_n), int(transponder))
                            self._log("CALLBACK", "Callback index eseguito con successo")
                        except Exception as ex:
                            self._log("CALLBACK", f"Errore callback on_transponder_received_index: {ex}")

                elif line.startswith("F:"):
                    # Protocollo comandi TCP in formato stringa: F:<CMD>
                    cmd_value = line.split(":", 1)[1].strip().upper()
                    if not cmd_value:
                        self._log("PARSER", f"{dev.device_id}: formato F non valido (comando vuoto): '{line}'")
                        continue

                    normalized_cmd = self._TCP_COMMAND_ALIASES.get(cmd_value, cmd_value)

                    is_known = (
                        normalized_cmd in self._VALID_TCP_COMMANDS
                        or cmd_value in self._SPECIAL_TCP_COMMANDS
                    )
                    if not is_known:
                        self._log("PARSER", f"{dev.device_id}: comando F sconosciuto '{cmd_value}'")
                        continue

                    self._log("PARSER", f"F ricevuto: device_id={dev.device_id} comando={cmd_value} normalizzato={normalized_cmd}")

                    if self.on_command_received:
                        try:
                            self.on_command_received(dev.device_id, cmd_value)
                        except Exception as ex:
                            self._log("CALLBACK", f"Errore callback on_command_received: {ex}")

                else:
                    self._log("RX", f"{dev.device_id}: frame non gestito '{line}'")

        except Exception as ex:
            self._log("RXLOOP", f"{dev.device_id}: errore RX loop: {ex}")

        finally:
            removed = self._disconnect_device(dev.device_id, reason="connessione chiusa", emit_alert=False)

            self._log("RXLOOP", f"RX loop terminato per {dev.device_id} (rimosso={removed})")

    # -------------------------
    # Commands
    # -------------------------
    def send_command(self, command: Union[str, DeviceCommand], device_id: Union[str, int]) -> None:
        if self.conn_type == ConnectionTypes.NONE:
            self._log("TX", f"NONE: comando '{command}' non inviato")
            return

        cmd_str = command.value if isinstance(command, DeviceCommand) else str(command)
        dev_key = f"D{int(device_id)}" if isinstance(device_id, (int, IntEnum)) else device_id

        with self._lock:
            dev = self._devices.get(dev_key)
            if dev is None:
                self._log("TX", f"{dev_key} non connesso → '{cmd_str}' non inviato")
                return

            try:
                dev.send_line(cmd_str)
                self._log("TX", f"{dev_key} <- '{cmd_str}'")
            except Exception as ex:
                self._log("TX", f"Errore invio '{cmd_str}' a {device_id}: {ex}")

    def broadcast(self, command: Union[str, DeviceCommand]) -> None:
        cmd_str = command.value if isinstance(command, DeviceCommand) else str(command)

        with self._lock:
            self._log("BROADCAST", f"Invio '{cmd_str}' a {len(self._devices)} dispositivo/i")
            for dev in list(self._devices.values()):
                try:
                    dev.send_line(cmd_str)
                    self._log("BROADCAST", f"{dev.device_id} <- '{cmd_str}'")
                except Exception as ex:
                    self._log("BROADCAST", f"Errore invio a {dev.device_id}: {ex}")

    # -------------------------
    # Info / Checks (VB port)
    # -------------------------
    def check_sectors_devices(self) -> bool:
        ok = len(self.active_flags) > 2 and self.active_flags[1] and self.active_flags[2]
        self.sectors_on = bool(ok)
        self._log("CHECK", f"check_sectors_devices → {ok}")
        return ok

    def check_pit_devices(self) -> bool:
        ok = len(self.active_flags) > 4 and self.active_flags[3] and self.active_flags[4]
        self.pit_on = bool(ok)
        self._log("CHECK", f"check_pit_devices → {ok}")
        return ok

    def all_required_devices_connected(self) -> bool:
        if self.conn_type == ConnectionTypes.NONE:
            state = (True, None)
            if self._last_required_devices_connected_state != state:
                self._last_required_devices_connected_state = state
            return True

        # LAPMONITOR: richiede BLE connesso + D5/D8 se abilitati
        if self.conn_type == ConnectionTypes.LAPMONITOR:
            if not self._ble_connected:
                state = (False, "BLE offline")
                if self._last_required_devices_connected_state != state:
                    self._last_required_devices_connected_state = state
                    self._log("CHECK", f"all_required_devices_connected → False (BLE offline)")
                return False
            
            # Controlla D5 e D8 se necessari
            missing: Optional[str] = None
            with self._lock:
                # D5 (Sem, index 5)
                if self.active_flags[5]:
                    if f"D5" not in self._devices:
                        missing = "D5 (Semaforo)"
                # D8 (RacePanel, index 8) - sempre richiesto se abilitato
                if self.active_flags[8]:
                    if f"D8" not in self._devices:
                        missing = "D8 (Race Panel)"
            
            ok = missing is None
            state = (ok, missing)
            if self._last_required_devices_connected_state != state:
                self._last_required_devices_connected_state = state
                self._log("CHECK", f"all_required_devices_connected (LAPMONITOR) → {ok} (BLE OK, mancante={missing})")
            return ok

        # TCP/SERIAL: controlla tutti i device richiesti
        missing: Optional[str] = None
        with self._lock:
            for i, required in enumerate(self.active_flags):
                if required:
                    dev_id = f"D{i}"
                    if dev_id not in self._devices:
                        missing = dev_id
                        break

        ok = missing is None
        state = (ok, missing)
        if self._last_required_devices_connected_state != state:
            self._last_required_devices_connected_state = state
            self._log("CHECK", f"all_required_devices_connected → {ok} (mancante={missing})")
        return ok

    # -------------------------
    # Parsing helpers (VB port)
    # -------------------------
    def _extract_device_id_and_ip(self, payload: str) -> tuple[str, str]:
        m = re.search(r"(D\d+)", payload)
        device_id = m.group(1) if m else "D?"

        m2 = re.search(rf"{re.escape(device_id)}IP(\d{{1,3}}(?:\.\d{{1,3}}){{3}})", payload)
        ip = m2.group(1) if m2 else "0"

        self._log("PARSER", f"_extract_device_id_and_ip: payload='{payload}' → ({device_id}, {ip})")
        return device_id, ip

    def _device_label(self, device_id: str) -> str:
        try:
            match = re.fullmatch(r"D(\d+)", str(device_id).strip())
            if match:
                index = int(match.group(1))
                if 0 <= index < len(self.DEVICE_NAMES):
                    return self.DEVICE_NAMES[index]
        except Exception:
            pass
        return str(device_id)

    # -------------------------
    # Logging
    # -------------------------
    def _log(self, tag: str, msg: str) -> None:
        _DEBUG_TAGS = {"RXLOOP", "RX", "PARSER", "CALLBACK", "HEARTBEAT"}
        if (not self.debug_log) and tag in _DEBUG_TAGS:
            return

        level = "ERROR" if tag == "ERROR" else ("DEBUG" if tag in _DEBUG_TAGS else "INFO")
        line = f"[DEVICE_MGR] {msg}"

        if self.on_log:
            try:
                self.on_log(line)
            except Exception as ex:
                log(f"[DEVICE_MGR] Errore callback on_log: {ex}", level="ERROR")

        log(line, level=level)
    
    def get_device_status_list(self) -> list[str]:
        """
        Restituisce una lista dello stato dei device:
        - Connesso (ONLINE) se il device ha completato l'handshake
        - Non connesso (OFFLINE) se ancora non collegato
        In LAPMONITOR: D0 via BLE, D1-D4 disabilitati, D5/D8 via TCP opzionali
        Compatibile con l'uso in _startup_win.update_status()
        """
        with self._lock:
            status_list = []
            for i, name in enumerate(self.DEVICE_NAMES):
                dev_id = f"D{i}"
                always_accepted = i in self._ALWAYS_ACCEPTED_IDS
                active = always_accepted or (i < len(self.active_flags) and self.active_flags[i])
                
                # LAPMONITOR mode: gestione specifica
                if self.conn_type == ConnectionTypes.LAPMONITOR:
                    if i == 0:  # Central (D0) → BLE LapMonitor
                        if self._ble_connected:
                            status_list.append(f"Device ID {i} - {name} - Connesso via BLE (LapMonitor)")
                        else:
                            status_list.append(f"Device ID {i} - {name} - BLE offline (LapMonitor)")
                    elif i in [1, 2, 3, 4]:  # D1-D4 disabilitati
                        status_list.append(f"Device ID {i} - {name} - Non usato in LAPMONITOR")
                    elif i in [5, 8] and active:  # D5 (Sem), D8 (RacePanel) se abilitati
                        if dev_id in self._devices:
                            ip = self._devices[dev_id].ip
                            status_list.append(f"Device ID {i} - {name} - Connesso da IP {ip}")
                        else:
                            status_list.append(f"Device ID {i} - {name} - In attesa di connessione (opzionale)...")
                    elif i in [5, 8]:
                        status_list.append(f"Device ID {i} - {name} - Non attivato dall'utente")
                    else:  # D6, D7
                        status_list.append(f"Device ID {i} - {name} - Non usato in LAPMONITOR")
                
                # TCP/SERIAL/NONE mode: logica standard
                elif not active:
                    status_list.append(f"Device ID {i} - {name} - Non attivato dall'utente")
                elif dev_id in self._devices:
                    ip = self._devices[dev_id].ip
                    status_list.append(f"Device ID {i} - {name} - Connesso da IP {ip}")
                elif always_accepted:
                    status_list.append(f"Device ID {i} - {name} - In attesa (opzionale)")
                else:
                    status_list.append(f"Device ID {i} - {name} - In attesa di connessione...")
            return status_list

    # -------------------------
    # BLE Gateway Callbacks (LAPMONITOR)
    # -------------------------
    def _on_ble_lap(self, car_id: int) -> None:
        """Callback da LapMonitor quando riceve un transponder via BLE."""
        self._log("BLE", f"Transponder ricevuto via BLE: car_id={car_id}")
        # Invia al device D0 (Central)
        if self.on_transponder_received_index:
            try:
                self.on_transponder_received_index(0, int(car_id))
            except Exception as ex:
                self._log("BLE", f"Errore callback on_transponder_received_index: {ex}")
    
    def _on_ble_status(self, connected: bool) -> None:
        """Callback da LapMonitor quando cambia lo stato della connessione BLE."""
        self._ble_connected = bool(connected)
        self._log("BLE", f"Stato BLE: {'CONNESSO' if connected else 'DISCONNESSO'}")
        
        # Notifica cambio stato device list
        if self.on_devices_changed:
            try:
                self.on_devices_changed()
            except Exception as ex:
                self._log("BLE", f"Errore callback on_devices_changed: {ex}")
        
        try:
            self.devicesChanged.emit()
        except Exception:
            pass