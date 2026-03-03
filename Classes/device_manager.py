from __future__ import annotations

import re
import socket
import threading
import time
from datetime import datetime
from enum import IntEnum
from typing import Callable, Dict, List, Optional, Sequence, Union

from Classes.device import Device
from Modules.device_commands import DeviceCommand
from Modules.log_utils import log  # logger tuo


class ConnectionTypes(IntEnum):
    NONE = 0
    TCP = 1
    LAPMONITOR = 2
    WIFIUDP = 3


class DeviceManager:
    class DevicesIDs(IntEnum):
        Central = 0
        S1 = 1
        S2 = 2
        PitIn = 3
        PitOut = 4
        Sem = 5
        AttZoneIn = 6
        AttZoneOut = 7

    class DeviceNames:
        LAP_DONE = "Lap Done"
        S1 = "Sect. 1"
        S2 = "Sect. 2"
        PIN = "Pit In"
        POUT = "Pit Out"
        SEM = "Semaforo"
        ATIN = "Att. Zone in"
        ATOUT = "Att. Zone Out"

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
    )
    MAX_DEVICES: int = len(DEVICE_NAMES)

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
                log(f"[SIM] simulate_transponder error: {ex}")

        # index listeners: (device, number)
        for fn in list(cls._transponder_simulated_index_listeners):
            try:
                fn(int(device), int(number))
            except Exception as ex:
                log(f"[SIM] simulate_transponder_index error: {ex}")

    def __init__(
        self,
        ip: str,
        port: int = 20777,
        conn_type: Union[int, ConnectionTypes] = ConnectionTypes.TCP,
        active_flags: Optional[Sequence[bool]] = None,
        handshake_delay_ms: int = 250,
        # debug: timeouts per evitare blocchi "muti"; None -> no timeout
        accept_timeout_s: Optional[float] = None,
        client_socket_timeout_s: Optional[float] = None,
    ) -> None:
        self.ip = ip
        self.port = port
        self.conn_type = ConnectionTypes(int(conn_type))

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

        self._devices: Dict[str, Device] = {}
        self._lock = threading.RLock()

        self._server_sock: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._is_running: bool = False

        # callbacks
        self.on_transponder_received: Optional[Callable[[str, int], None]] = None
        self.on_transponder_received_index: Optional[Callable[[int, int], None]] = None  # NEW
        self.on_log: Optional[Callable[[str], None]] = None

        self._handshake_delay_s = max(0.0, handshake_delay_ms / 1000.0)
        self._accept_timeout_s = None if accept_timeout_s is None else float(accept_timeout_s)
        self._client_socket_timeout_s = None if client_socket_timeout_s is None else float(client_socket_timeout_s)

        self._log("INIT", f"DeviceManager created ip={ip} port={port} conn_type={self.conn_type.name}")
        self._log("INIT", f"MAX_DEVICES={self.MAX_DEVICES} DEVICE_NAMES={list(self.DEVICE_NAMES)}")
        self._log("INIT", f"active_flags={self.active_flags}")
        self._log("INIT", f"handshake_delay_s={self._handshake_delay_s}")
        self._log("INIT", f"accept_timeout_s={self._accept_timeout_s} client_socket_timeout_s={self._client_socket_timeout_s} (None means no timeout)")

        if self.conn_type == ConnectionTypes.TCP:
            self.start()

    # -------------------------
    # Lifecycle
    # -------------------------
    def start(self) -> None:
        self._log("START", "start() called")
        self._log("START", f"DeviceManager config: ip={self.ip}, port={self.port}, conn_type={self.conn_type.name}")

        if self.conn_type == ConnectionTypes.NONE:
            self._log("START", "ConnectionTypes.NONE -> server not started")
            return

        if self._is_running:
            self._log("START", "Already running")
            return

        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            self._log("START", f"⚠️ IMPORTANT: Server will listen on 0.0.0.0:{self.port} (all interfaces)")
            self._log("START", f"⚠️ Connect to: {self.ip}:{self.port} from external device")
            self._log("START", f"Binding 0.0.0.0:{self.port}")
            self._server_sock.bind(("0.0.0.0", self.port))

            self._server_sock.listen(20)
            if self._accept_timeout_s is not None:
                self._server_sock.settimeout(self._accept_timeout_s)

            self._is_running = True
            self._log("START", f"Server listening on port {self.port}")

            self._accept_thread = threading.Thread(
                target=self._accept_clients_loop,
                daemon=True,
                name="DM-AcceptLoop",
            )
            self._accept_thread.start()
            self._log("START", "Accept loop thread started")

        except Exception as ex:
            self._log("ERROR", f"start() failed: {ex}")

    def disconnect_all(self) -> None:
        self._log("STOP", "disconnect_all() called")

        self._is_running = False

        with self._lock:
            self._log("STOP", f"Closing {len(self._devices)} device(s)")
            for dev in list(self._devices.values()):
                try:
                    self._log("STOP", f"{dev.device_id}: send DSCN")
                    dev.send_line(DeviceCommand.DSCN.value)
                except Exception as ex:
                    self._log("STOP", f"{dev.device_id}: DSCN send error: {ex}")

                try:
                    self._log("STOP", f"{dev.device_id}: close()")
                    dev.close()
                except Exception as ex:
                    self._log("STOP", f"{dev.device_id}: close error: {ex}")

            self._devices.clear()

        if self._server_sock is not None:
            try:
                self._log("STOP", "Closing server socket")
                self._server_sock.close()
                self._log("STOP", "Server socket closed")
            except Exception as ex:
                self._log("STOP", f"Server socket close error: {ex}")
            finally:
                self._server_sock = None

    # -------------------------
    # Accept / handshake
    # -------------------------
    def _accept_clients_loop(self) -> None:
        if self._server_sock is None:
            self._log("ACCEPT", "Server socket is None -> accept loop exit")
            return

        self._log("ACCEPT", "Accept loop started")

        while self._is_running:
            try:
                self._log("ACCEPT", "Waiting for client (accept)...")
                client_sock, addr = self._server_sock.accept()

                self._log("ACCEPT", f"Client connected from {addr}")

                # timeout per evitare blocchi su recv/readline
                if self._client_socket_timeout_s is not None:
                    client_sock.settimeout(self._client_socket_timeout_s)

                rfile = client_sock.makefile("r", encoding="ascii", newline="\n")
                wfile = client_sock.makefile("w", encoding="ascii", newline="\n")

                # Handshake: invia "C"
                wfile.write(f"{DeviceCommand.CONN.value}\n")
                wfile.flush()
                self._log("HANDSHAKE", f"Sent handshake '{DeviceCommand.CONN.value}'")

                time.sleep(self._handshake_delay_s)

                self._log("HANDSHAKE", "Reading handshake response (readline)...")
                response = rfile.readline()
                response = response.strip() if response else ""
                self._log("HANDSHAKE", f"Response='{response}'")

                if not response.startswith(f"{DeviceCommand.CONN.value}:"):
                    self._log("HANDSHAKE", "Invalid handshake. Closing client.")
                    try:
                        client_sock.close()
                    except Exception as ex:
                        self._log("HANDSHAKE", f"Client close error: {ex}")
                    continue

                payload = response.split(":", 1)[1]
                device_id, device_ip = self._extract_device_id_and_ip(payload)
                self._log("HANDSHAKE", f"Parsed payload='{payload}' -> device_id={device_id} ip={device_ip}")

                with self._lock:
                    if device_id in self._devices:
                        self._log("HANDSHAKE", f"{device_id} already connected -> refuse")
                        try:
                            client_sock.close()
                        except Exception as ex:
                            self._log("HANDSHAKE", f"Client close error: {ex}")
                        continue

                    dev = Device(
                        device_id=device_id,
                        ip=device_ip,
                        sock=client_sock,
                        _rfile=rfile,
                        _wfile=wfile,
                    )
                    self._devices[device_id] = dev

                self._log("ACCEPT", f"Registered device {device_id}")

                t = threading.Thread(
                    target=self._receive_loop,
                    args=(dev,),
                    daemon=True,
                    name=f"DM-RX-{device_id}",
                )
                t.start()
                self._log("ACCEPT", f"RX thread started for {device_id}")

            except socket.timeout:
                # if using a timeout, loop again; otherwise this block won't be hit
                if self._accept_timeout_s is not None:
                    continue
            except OSError as ex:
                self._log("ACCEPT", f"OSError (likely stop): {ex}")
                break
            except Exception as ex:
                self._log("ACCEPT", f"Client accept/handshake error: {ex}")

        self._log("ACCEPT", "Accept loop ended")

    # -------------------------
    # Receive loop
    # -------------------------
    def _receive_loop(self, dev: Device) -> None:
        self._log("RXLOOP", f"Start RX loop for {dev.device_id}")

        try:
            while self._is_running:
                self._log("RXLOOP", f"{dev.device_id}: waiting read_line()")
                line = dev.read_line()

                if line is None:
                    self._log("RXLOOP", f"{dev.device_id}: read_line() -> None (disconnect)")
                    break

                raw = line
                line = line.strip()
                if not line:
                    self._log("RX", f"{dev.device_id}: empty line ignored (raw={raw!r})")
                    continue

                self._log("RX", f"{dev.device_id} -> {line}")

                if line.startswith("P:"):
                    m = re.match(r"^P:D(\d+)T(\d+)$", line)
                    if not m:
                        self._log("PARSER", f"{dev.device_id}: invalid P format: '{line}'")
                        continue

                    dev_n = int(m.group(1))
                    transponder = int(m.group(2))
                    device_id = f"D{dev_n}"

                    self._log("PARSER", f"P OK: device_id={device_id} transponder={transponder}")

                    # legacy callback: ("D0", 22)
                    if self.on_transponder_received:
                        try:
                            #self._log("CALLBACK", f"Calling on_transponder_received({device_id}, {transponder})")
                            self.on_transponder_received(device_id, transponder)
                            #self._log("CALLBACK", "Callback OK")
                        except Exception as ex:
                            self._log("CALLBACK", f"Callback error: {ex}")

                    # NEW callback: (0, 22)
                    if self.on_transponder_received_index:
                        try:
                            self._log("CALLBACK", f"Calling on_transponder_received_index({dev_n}, {transponder})")
                            self.on_transponder_received_index(int(dev_n), int(transponder))
                            self._log("CALLBACK", "Callback index OK")
                        except Exception as ex:
                            self._log("CALLBACK", f"Callback index error: {ex}")

                else:
                    self._log("RX", f"{dev.device_id}: unhandled frame '{line}'")

        except Exception as ex:
            self._log("RXLOOP", f"{dev.device_id}: RX loop error: {ex}")

        finally:
            with self._lock:
                removed = self._devices.pop(dev.device_id, None) is not None

            try:
                dev.close()
            except Exception as ex:
                self._log("RXLOOP", f"{dev.device_id}: close error: {ex}")

            self._log("RXLOOP", f"End RX loop for {dev.device_id} (removed={removed})")

    # -------------------------
    # Commands
    # -------------------------
    def send_command(self, command: Union[str, DeviceCommand], device_id: str) -> None:
        if self.conn_type == ConnectionTypes.NONE:
            self._log("TX", f"NONE: command '{command}' not sent")
            return

        cmd_str = command.value if isinstance(command, DeviceCommand) else str(command)

        with self._lock:
            dev = self._devices.get(device_id)
            if dev is None:
                self._log("TX", f"{device_id} not connected -> cmd '{cmd_str}' not sent")
                return

            try:
                dev.send_line(cmd_str)
                self._log("TX", f"{device_id} <- '{cmd_str}'")
            except Exception as ex:
                self._log("TX", f"{device_id}: send error '{cmd_str}': {ex}")

    def broadcast(self, command: Union[str, DeviceCommand]) -> None:
        cmd_str = command.value if isinstance(command, DeviceCommand) else str(command)

        with self._lock:
            self._log("BROADCAST", f"Sending '{cmd_str}' to {len(self._devices)} device(s)")
            for dev in list(self._devices.values()):
                try:
                    dev.send_line(cmd_str)
                    self._log("BROADCAST", f"{dev.device_id} <- '{cmd_str}'")
                except Exception as ex:
                    self._log("BROADCAST", f"{dev.device_id}: send error: {ex}")

    # -------------------------
    # Info / Checks (VB port)
    # -------------------------
    def check_sectors_devices(self) -> bool:
        ok = len(self.active_flags) > 2 and self.active_flags[1] and self.active_flags[2]
        self.sectors_on = bool(ok)
        self._log("CHECK", f"check_sectors_devices -> {ok}")
        return ok

    def check_pit_devices(self) -> bool:
        ok = len(self.active_flags) > 4 and self.active_flags[3] and self.active_flags[4]
        self.pit_on = bool(ok)
        self._log("CHECK", f"check_pit_devices -> {ok}")
        return ok

    def all_required_devices_connected(self) -> bool:
        if self.conn_type == ConnectionTypes.NONE:
            return True

        missing: Optional[str] = None
        with self._lock:
            for i, required in enumerate(self.active_flags):
                if required:
                    dev_id = f"D{i}"
                    if dev_id not in self._devices:
                        missing = dev_id
                        break

        ok = missing is None
        self._log("CHECK", f"all_required_devices_connected -> {ok} (missing={missing})")
        return ok

    # -------------------------
    # Parsing helpers (VB port)
    # -------------------------
    def _extract_device_id_and_ip(self, payload: str) -> tuple[str, str]:
        m = re.search(r"(D\d+)", payload)
        device_id = m.group(1) if m else "D?"

        m2 = re.search(rf"{re.escape(device_id)}IP(\d{{1,3}}(?:\.\d{{1,3}}){{3}})", payload)
        ip = m2.group(1) if m2 else "0"

        self._log("PARSER", f"_extract_device_id_and_ip payload='{payload}' -> ({device_id}, {ip})")
        return device_id, ip

    # -------------------------
    # Logging
    # -------------------------
    def _log(self, tag: str, msg: str) -> None:
        line = f"[{tag}] {msg}"

        if self.on_log:
            try:
                self.on_log(line)
            except Exception as ex:
                log(f"{datetime.now().isoformat(timespec='milliseconds')} | [LOG] on_log callback error: {ex}")

        log(line)
    
    def get_device_status_list(self) -> list[str]:
        """
        Restituisce una lista dello stato dei device:
        - Connesso (ONLINE) se il device ha completato l'handshake
        - Non connesso (OFFLINE) se ancora non collegato
        Compatibile con l'uso in _startup_win.update_status()
        """
        with self._lock:
            status_list = []
            for i, name in enumerate(self.DEVICE_NAMES):
                dev_id = f"D{i}"
                if i >= len(self.active_flags) or not self.active_flags[i]:
                    status_list.append(f"Device ID {i} - {name} - Non attivato dall'utente")
                elif dev_id in self._devices:
                    ip = self._devices[dev_id].ip
                    status_list.append(f"Device ID {i} - {name} - Connesso da IP {ip}")
                else:
                    status_list.append(f"Device ID {i} - {name} - In attesa di connessione...")
            return status_list