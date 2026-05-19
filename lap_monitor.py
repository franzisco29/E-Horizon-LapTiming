"""
BLE Gateway per LapMonitor - Nordic UART Service (NUS)

Utilizza Bleak per connettersi a dispositivi BLE LapMonitor e leggere
i transponder via Nordic UART Service (NUS) con frame parsing.

Callbacks:
  - on_lap(car_id: int)           # nuovo giro ricevuto
  - on_status(connected: bool)    # cambio stato connessione
"""

import asyncio
import threading
import time
from typing import Callable, Optional

try:
    from bleak import BleakClient
except ImportError:
    BleakClient = None  # type: ignore


class LapMonitor:
    """
    Gateway BLE per LapMonitor device.
    
    Legge transponder via Nordic UART Service (NUS):
      RX UUID: 6e400003-b5a3-f393-e0a9-e50e24dcca9e  (notify)
      TX UUID: 6e400002-b5a3-f393-e0a9-e50e24dcca9e  (write)
    
    Frame format:
      [... 0x23 0x6C ... car_id @ offset 7 ...]
    """
    
    # Nordic UART Service UUIDs
    RX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # notify
    TX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # write
    FRAME_MARKER = b"\x23\x6c"  # 0x23 0x6c

    @staticmethod
    def build_config_packet(min_lap_s: int) -> bytearray:
        """
        Unico pacchetto inviato al dispositivo BLE dopo la connessione.

        Struttura (19 byte):
            [0]  = 35   '#'
            [1]  = 83   'S'
            [2]  = 0
            [3]  = 0
            [4]  = 0
            [15] = 127
            [16] = 127
            [17] = 0
            [18] = min_lap_s
        """
        v = max(0, min(255, int(min_lap_s)))
        pkt = bytearray(19)
        pkt[0] = 35
        pkt[1] = 83
        pkt[15] = 127
        pkt[16] = 127
        pkt[18] = v
        return pkt
    
    def __init__(
        self,
        address: str,
        min_lap_s: float = 5.0,
        reconnect_s: float = 3.0,
        debug: bool = False,
    ):
        """
        Args:
            address: BLE MAC address (es. "70:B3:D5:4B:E2:95")
            min_lap_s: Debounce minimo tra lap consecutivi (deprecated, use race_manager debounce)
            reconnect_s: Intervallo di riconnessione (default 3s)
            debug: Log verboso
        """
        if BleakClient is None:
            raise ImportError("Bleak non installato. Installa con: pip install bleak")
        
        self.address = address.lower()
        self.min_lap_s = float(min_lap_s)
        self.reconnect_s = float(reconnect_s)
        self.debug = bool(debug)
        
        # Callbacks
        self.on_lap: Optional[Callable[[int], None]] = None
        self.on_status: Optional[Callable[[bool], None]] = None
        
        # State
        self._connected = False
        self._client: Optional[BleakClient] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._last_car_id: Optional[int] = None
        self._last_lap_time: float = 0.0
        
    def _log(self, msg: str) -> None:
        if self.debug:
            print(f"[LapMonitor] {msg}")
    
    def start(self) -> None:
        """Avvia il monitor BLE in un thread separato."""
        if self._running:
            self._log("Già in esecuzione")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True, name="LapMonitor-BLE")
        self._thread.start()
        self._log(f"Monitor avviato per {self.address}")
    
    def stop(self) -> None:
        """Ferma il monitor BLE."""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._stop_async)
        if self._thread:
            self._thread.join(timeout=2.0)
        self._log("Monitor fermato")
    
    def _run_async_loop(self) -> None:
        """Ciclo asincrono in thread dedicato."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connection_loop())
        finally:
            self._loop.close()
            self._loop = None
    
    async def _connection_loop(self) -> None:
        """Loop di connessione con auto-reconnect."""
        while self._running:
            try:
                await self._connect_and_read()
            except Exception as e:
                self._log(f"Errore connessione: {e}")
                self._set_connected(False)
            
            if self._running:
                await asyncio.sleep(self.reconnect_s)
    
    async def _connect_and_read(self) -> None:
        """Connetti e leggi dati dal device."""
        self._client = BleakClient(self.address)
        self._log(f"Connessione a {self.address}...")
        
        try:
            await self._client.connect(timeout=10.0)
            self._log(f"Connesso a {self.address}")

            # Pacchetto di start/config obbligatorio per abilitare la trasmissione giri.
            try:
                cfg_packet = self.build_config_packet(int(self.min_lap_s))
                await self._client.write_gatt_char(self.TX_UUID, cfg_packet, response=False)
                self._log(f"Pacchetto start inviato ({len(cfg_packet)} byte)")
            except Exception as ex:
                self._log(f"Errore invio pacchetto start: {ex}")
                raise

            self._set_connected(True)
            
            # Iscriviti a notifiche dal RX characteristic
            await self._client.start_notify(self.RX_UUID, self._on_notification)
            
            # Mantieni la connessione aperta
            while self._running and self._client and self._client.is_connected:
                await asyncio.sleep(0.5)
        
        except Exception as e:
            self._log(f"Errore during connect/notify: {e}")
            self._set_connected(False)
        
        finally:
            if self._client:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass
                self._client = None
            self._set_connected(False)
    
    def _on_notification(self, sender: int, data: bytearray) -> None:
        """Callback quando ricevi dati via BLE."""
        try:
            self._parse_frame(bytes(data))
        except Exception as e:
            self._log(f"Errore parsing frame: {e}")
    
    def _parse_frame(self, frame: bytes) -> None:
        """Parsa frame Nordic UART e estrae car_id."""
        # Cerca marker 0x23 0x6c
        marker_pos = frame.find(self.FRAME_MARKER)
        if marker_pos < 0:
            return
        
        # car_id a offset 7 dal marker
        car_id_offset = marker_pos + 7
        if car_id_offset >= len(frame):
            return
        
        car_id = frame[car_id_offset]
        
        # Debounce: ignora se è lo stesso car_id entro min_lap_s
        now = time.time()
        if self._last_car_id == car_id and (now - self._last_lap_time) < self.min_lap_s:
            return
        
        self._last_car_id = car_id
        self._last_lap_time = now
        
        # Callback
        if self.on_lap:
            try:
                self.on_lap(int(car_id))
                self._log(f"Lap ricevuto: car_id={car_id}")
            except Exception as e:
                self._log(f"Errore callback on_lap: {e}")
    
    def _set_connected(self, connected: bool) -> None:
        """Aggiorna stato connessione e chiama callback."""
        if self._connected != connected:
            self._connected = connected
            self._log(f"Status: {'CONNESSO' if connected else 'DISCONNESSO'}")
            
            if self.on_status:
                try:
                    self.on_status(connected)
                except Exception as e:
                    self._log(f"Errore callback on_status: {e}")
    
    async def _stop_async(self) -> None:
        """Stop asincrono (da chiamare da _run_async_loop)."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
    
    @property
    def is_connected(self) -> bool:
        """Stato della connessione BLE."""
        return self._connected
