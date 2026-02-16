from __future__ import annotations

import socket
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TextIO


@dataclass
class Device:
    """
    Dispositivo connesso (equivalente VB class Device).
    Gestisce socket + reader/writer ASCII in modalità line-based.
    """
    device_id: str         # es: "D1"
    ip: str                # ip del device (da handshake)
    sock: socket.socket

    _rfile: TextIO = field(repr=False)
    _wfile: TextIO = field(repr=False)

    last_status_response: datetime = field(default_factory=datetime.now)
    _write_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def send_line(self, line: str) -> None:
        """Invia una riga ASCII terminata da newline (WriteLine VB)."""
        if not line.endswith("\n"):
            line += "\n"
        with self._write_lock:
            try:
                self._wfile.write(line)
                self._wfile.flush()
            except Exception:
                # gestione errori/log a livello manager
                pass

    def read_line(self) -> Optional[str]:
        """Legge una riga (ReadLine VB). Ritorna None su EOF/disconnessione."""
        try:
            s = self._rfile.readline()
            if s == "":
                return None
            return s.rstrip("\r\n")
        except Exception:
            return None

    def close(self) -> None:
        """Chiude flussi e socket."""
        try:
            try:
                self._rfile.close()
            except Exception:
                pass
            try:
                self._wfile.close()
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
        finally:
            pass
