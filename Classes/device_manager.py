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


class ConnectionTypes(IntEnum):
    NONE = 0
    TCP = 1
    LAPMONITOR = 2
    WIFIUDP = 3


class DeviceManager:
    """
    VB DeviceManager -> Python

    - Server TCP che accetta fino a MAX_DEVICES
    - Handshake: invia CONN_CMD, aspetta risposta "C:D1IPx.x.x.x"
    - Per ogni device: thread di ricezione line-based
    - Ping STATUS periodico per rilevare inattività/disconnessioni
    - Eventi VB -> callback:
        on_transponder_received(device_id: str, transponder_id: int)
        on_log(message: str)
    """

    MAX_DEVICES: int = 6
    DEVICE_NAMES: Sequence[str] = (
        "Lap Done", "Sect. 1", "Sect. 2", "Pit In", "Pit Out", "Semaforo"
    )

    # "Shared Event" in VB (simulazione transponder)
    _transponder_simulated_listeners: List[Callable[[int, int], None]] = []

    @classmethod
    def add_transponder_simulated_listener(cls, fn: Callable[[int, int], None]) -> None:
        cls._transponder_simulated_listeners.append(fn)

    @classmethod
    def simulate_transponder(cls, number: int, device: int) -> None:
        for fn in list(cls._transponder_simulated_listeners):
            try:
                fn(number, device)
            except Exception:
                pass

    def __init__(
        self,
        ip: str,
        port: int = 20777,
        conn_type: Union[int, ConnectionTypes] = ConnectionTypes.TCP,
        active_flags: Optional[Sequence[bool]] = None,
        ping_interval_s: float = 4.0,
        status_timeout_s: float = 10.0,
        handshake_delay_ms: int = 250,
    ) -> None:
        self.ip = ip
        self.port = port
        self.conn_type = ConnectionTypes(int(conn_type))

        # VB: activeFlags da settings "1,0,1,..."
        self.active_flags: List[bool] = (
            list(active_flags) if active_flags is not None else [True] * self.MAX_DEVICES
        )

        self.sectors_on: bool = False
        self.pit_on: bool = False

        self._devices: Dict[str, Device] = {}
        self._lock = threading.RLock()

        self._server_sock: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._is_running: bool = False

        self.on_transponder_received: Optional[Callable[[str, int], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None

        self._ping_interval_s = float(ping_interval_s)
        self._status_timeout_s = float(status_timeout_s)
        self._handshake_delay_s = max(0.0, handshake_delay_ms / 1000.0)

        self._ping_timer: Optional[threading.Timer] = None

        if self.conn_type == ConnectionTypes.TCP:
            self.start()

    # -------------------------
    # Lifecycle
    # -------------------------
    def start(self) -> None:
        if self.conn_type == ConnectionTypes.NONE:
            self._log("[!] ConnectionTypes.NONE: server non avviato.")
            return
        if self._is_running:
            return

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(("0.0.0.0", self.port))
        self._server_sock.listen(20)

        self._is_running = True
        self._log(f"[Server] In ascolto su porta {self.port}")

        self._accept_thread = threading.Thread(target=self._accept_clients_loop, daemon=True)
        self._accept_thread.start()

        self._start_ping_timer()

    def disconnect_all(self) -> None:
        self._is_running = False
        self._stop_ping_timer()

        # chiudi tutti i device
        with self._lock:
            for dev in list(self._devices.values()):
                try:
                    dev.send_line(DeviceCommand.DSCN.value)
                except Exception:
                    pass
                dev.close()
            self._devices.clear()

        # chiudi listener
        if self._server_sock is not None:
            try:
                self._server_sock.close()
                self._log("[SERVER] Arrestato.")
            except Exception as ex:
                self._log(f"[!] Errore durante arresto del listener: {ex}")
            finally:
                self._server_sock = None

    # -------------------------
    # Accept / handshake
    # -------------------------
    def _accept_clients_loop(self) -> None:
        assert self._server_sock is not None

        while self._is_running:
            try:
                client_sock, _addr = self._server_sock.accept()
                client_sock.settimeout(None)

                rfile = client_sock.makefile("r", encoding="ascii", newline="\n")
                wfile = client_sock.makefile("w", encoding="ascii", newline="\n")

                # Handshake: invia "C"
                wfile.write(f"{DeviceCommand.CONN.value}\n")
                wfile.flush()
                self._log(f"[Server] Inviato comando handshake '{DeviceCommand.CONN.value}' al nuovo dispositivo")

                time.sleep(self._handshake_delay_s)

                response = rfile.readline()
                response = response.strip() if response else ""

                if not response.startswith(f"{DeviceCommand.CONN.value}:"):
                    self._log("[!] Handshake non valido. Connessione rifiutata.")
                    try:
                        client_sock.close()
                    except Exception:
                        pass
                    continue

                # payload tipo: D1IP192.168.1.50
                payload = response.split(":", 1)[1]
                device_id, device_ip = self._extract_device_id_and_ip(payload)

                with self._lock:
                    if device_id in self._devices:
                        self._log(f"[!] Dispositivo {device_id} già connesso. Connessione rifiutata.")
                        try:
                            client_sock.close()
                        except Exception:
                            pass
                        continue

                    dev = Device(device_id=device_id, ip=device_ip, sock=client_sock, _rfile=rfile, _wfile=wfile)
                    dev.last_status_response = datetime.now()
                    self._devices[device_id] = dev

                self._log(f"[+] Registrato nuovo dispositivo {device_id}")

                t = threading.Thread(target=self._receive_loop, args=(dev,), daemon=True)
                t.start()

            except OSError:
                # socket chiuso mentre stai stoppando
                break
            except Exception as ex:
                self._log(f"[!] Errore connessione client: {ex}")

    # -------------------------
    # Receive loop
    # -------------------------
    def _receive_loop(self, dev: Device) -> None:
        try:
            while self._is_running:
                line = dev.read_line()
                if line is None:
                    break
                if not line.strip():
                    continue

                self._log(f"[RX] {line}")

                if line.startswith("P:"):
                    # VB: "P:D(\d+)T(\d+)"
                    m = re.match(r"^P:D(\d+)T(\d+)$", line.strip())
                    if m:
                        dev_n = int(m.group(1))
                        transponder = int(m.group(2))
                        device_id = f"D{dev_n}"

                        if self.on_transponder_received:
                            try:
                                self.on_transponder_received(device_id, transponder)
                            except Exception:
                                pass

                        self._log(f"[!] Transponder ricevuto da {device_id}: {transponder}")

                elif line.startswith("S:"):
                    self._log(f"[STATO] {line}")
                    dev.last_status_response = datetime.now()

        except Exception:
            self._log(f"[!] Connessione persa con {dev.device_id}")
        finally:
            with self._lock:
                self._devices.pop(dev.device_id, None)
            dev.close()

    # -------------------------
    # Commands
    # -------------------------
    def send_command(self, command: Union[str, DeviceCommand], device_id: str) -> None:
        if self.conn_type == ConnectionTypes.NONE:
            self._log(f"[!] Nessuna connessione attiva. Comando '{command}' non inviato.")
            return

        cmd_str = command.value if isinstance(command, DeviceCommand) else str(command)

        with self._lock:
            dev = self._devices.get(device_id)
            if dev is None:
                self._log(f"[!] Dispositivo {device_id} non connesso.")
                return

            dev.send_line(cmd_str)
            self._log(f"[TX] Comando '{cmd_str}' inviato a {device_id}")

    def broadcast(self, command: Union[str, DeviceCommand]) -> None:
        cmd_str = command.value if isinstance(command, DeviceCommand) else str(command)

        with self._lock:
            for dev in list(self._devices.values()):
                dev.send_line(cmd_str)
                self._log(f"[BROADCAST] '{cmd_str}' inviato a {dev.device_id}")

    # -------------------------
    # Status / Ping
    # -------------------------
    def _start_ping_timer(self) -> None:
        self._stop_ping_timer()

        def tick():
            if not self._is_running:
                return
            try:
                self.ping_devices()
            finally:
                self._ping_timer = threading.Timer(self._ping_interval_s, tick)
                self._ping_timer.daemon = True
                self._ping_timer.start()

        self._ping_timer = threading.Timer(self._ping_interval_s, tick)
        self._ping_timer.daemon = True
        self._ping_timer.start()

    def _stop_ping_timer(self) -> None:
        if self._ping_timer is not None:
            try:
                self._ping_timer.cancel()
            except Exception:
                pass
            self._ping_timer = None

    def ping_devices(self) -> None:
        now = datetime.now()

        with self._lock:
            to_remove: List[str] = []

            for dev_id, dev in list(self._devices.items()):
                try:
                    dev.send_line(DeviceCommand.STATUS.value)
                    seconds = (now - dev.last_status_response).total_seconds()

                    if seconds > self._status_timeout_s:
                        self._log(f"[!] Dispositivo {dev_id} non ha risposto a STATUS negli ultimi {int(seconds)}s.")
                        to_remove.append(dev_id)
                except Exception as ex:
                    self._log(str(ex))

            for dev_id in to_remove:
                dev = self._devices.get(dev_id)
                if dev:
                    dev.close()
                self._devices.pop(dev_id, None)
                self._log(f"[!] Dispositivo {dev_id} rimosso per inattività.")

    # -------------------------
    # Info / Checks (VB port)
    # -------------------------
    def print_status(self) -> None:
        self._log("===== STATO DEVICE MANAGER =====")
        with self._lock:
            for i in range(self.MAX_DEVICES):
                dev_id = f"D{i}"
                connected = "Connesso" if dev_id in self._devices else "Non connesso"
                attivo = "SI" if i < len(self.active_flags) and self.active_flags[i] else "NO"
                self._log(f"Device {dev_id} | Attivo: {attivo} | Stato: {connected}")

    def check_sectors_devices(self) -> bool:
        if len(self.active_flags) > 2 and self.active_flags[1] and self.active_flags[2]:
            self.sectors_on = True
            return True
        return False

    def check_pit_devices(self) -> bool:
        if len(self.active_flags) > 4 and self.active_flags[3] and self.active_flags[4]:
            self.pit_on = True
            return True
        return False

    def get_device_status_list(self) -> List[str]:
        status_list: List[str] = []

        with self._lock:
            for i, name in enumerate(self.DEVICE_NAMES):
                if i >= len(self.active_flags) or not self.active_flags[i]:
                    status_list.append(f"Device ID {i} - {name} - Non attivato dall'utente")
                    continue

                dev_id = f"D{i}"
                if self.conn_type != ConnectionTypes.NONE:
                    if dev_id in self._devices:
                        ip = self._devices[dev_id].ip
                        status_list.append(f"Device ID {i} - {name} - Connesso da IP {ip}")
                    else:
                        status_list.append(f"Device ID {i} - {name} - In attesa di connessione...")
                else:
                    status_list.append(f"Device ID {i} - {name} - Connesso")

        return status_list

    def all_required_devices_connected(self) -> bool:
        if self.conn_type == ConnectionTypes.NONE:
            return True

        with self._lock:
            for i, required in enumerate(self.active_flags):
                if required:
                    dev_id = f"D{i}"
                    if dev_id not in self._devices:
                        return False
        return True

    # -------------------------
    # Parsing helpers (VB port)
    # -------------------------
    def _extract_device_id_and_ip(self, payload: str) -> tuple[str, str]:
        """
        payload es: "D1IP192.168.1.50"
        ritorna ("D1", "192.168.1.50")
        """
        m = re.search(r"(D\d+)", payload)
        device_id = m.group(1) if m else "D?"

        m2 = re.search(rf"{re.escape(device_id)}IP(\d{{1,3}}(?:\.\d{{1,3}}){{3}})", payload)
        ip = m2.group(1) if m2 else "0"
        return device_id, ip

    # -------------------------
    # Logging
    # -------------------------
    def _log(self, msg: str) -> None:
        if self.on_log:
            try:
                self.on_log(msg)
                return
            except Exception:
                pass
        print(msg)
