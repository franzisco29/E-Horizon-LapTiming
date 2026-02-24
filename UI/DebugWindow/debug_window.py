from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget, QMessageBox

from Modules.log_utils import log  # :contentReference[oaicite:2]{index=2}
from UI.DebugWindow.debug_window_ui import DebugWindowUI


@dataclass
class DebugDriverView:
    number: int
    label: str


class DebugWindow(QDialog):
    """
    Porting VB DebugForm:
    - riceve numbers + drivers
    - crea righe dinamiche con 5 pulsanti
    - click -> DeviceManager.simulate_transponder(number, device)  <-- ORDINE CORRETTO
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        numbers: List[int],
        drivers: List[object],
        device_manager: object,
    ):
        super().__init__(parent)

        self.numbers = list(numbers)
        self.drivers = list(drivers)
        self.device_manager = device_manager

        # IMPORTANT: teniamo references ai callback per evitare sorprese
        self._handlers: list[Callable[[], None]] = []

        log(f"[DebugWindow] __init__ numbers={self.numbers} drivers={len(self.drivers)} device_manager={type(self.device_manager)}")

        self.ui = DebugWindowUI(self)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.addWidget(self.ui)

        self.setWindowTitle("E-Horizon • Debug")
        self.resize(980, 620)

        self.create_rows()

    def _find_driver_label_by_number(self, number: int) -> str:
        for d in self.drivers:
            n = getattr(d, "Number", None)
            if n is None:
                n = getattr(d, "number", None)
            if n is None:
                continue
            if int(n) == int(number):
                label = getattr(d, "nameSurnameForResult", None)
                if label is None:
                    name = getattr(d, "name", "")
                    surname = getattr(d, "surname", "")
                    label = f"{name} {surname}".strip()
                return str(label)
        return f"Driver #{number:02d}"

    def create_rows(self) -> None:
        log("[DebugWindow] create_rows() start")
        self._handlers.clear()

        # pulizia UI
        try:
            self.ui.clear_rows()
        except Exception as e:
            log(f"[DebugWindow] ui.clear_rows() ERROR: {e}")
            raise

        if not self.numbers:
            log("[DebugWindow] No numbers -> add placeholder row")
            try:
                self.ui.add_row("No numbers provided", -1, lambda *_: (lambda: None))
            except Exception as e:
                log(f"[DebugWindow] ui.add_row(placeholder) ERROR: {e}")
            return

        def callback_factory(device: int, number: int):
            """
            UI dovrebbe chiamare questa factory per ogni bottone:
              handler = callback_factory(device, number)
              button.clicked.connect(handler)
            """
            log(f"[DebugWindow] callback_factory(device={device}, number={number})")

            def handler():
                log(f"[DebugWindow] CLICK -> device={device} number={number}")
                self.send_udp_message(device=device, number=number)

            # teniamo il riferimento
            self._handlers.append(handler)
            return handler

        for number in self.numbers:
            try:
                label = self._find_driver_label_by_number(int(number))
                log(f"[DebugWindow] add_row label='{label}' number={int(number)}")
                self.ui.add_row(label, int(number), callback_factory)
            except Exception as e:
                log(f"[DebugWindow] add_row ERROR number={number}: {e}")

        log("[DebugWindow] create_rows() end")

    def send_udp_message(self, *, device: int, number: int) -> None:
        log(f"[DebugWindow] send_udp_message(device={device}, number={number})")

        # nel tuo form VB erano 5 pulsanti -> 0..4
        if device < 0 or device > 4:
            log("[DebugWindow] device out of range (0..4) -> ignored")
            return

        if number < 0 or number > 99:
            log("[DebugWindow] number out of range (0..99) -> warning")
            QMessageBox.warning(self, "Debug", "Number must be between 0 and 99.")
            return

        try:
            # ✅ ORDINE CORRETTO: simulate_transponder(number, device)
            if hasattr(self.device_manager, "simulate_transponder"):
                log("[DebugWindow] calling device_manager.simulate_transponder(number, device)")
                self.device_manager.simulate_transponder(int(number), int(device))
            elif hasattr(self.device_manager, "SimulateTransponder"):
                log("[DebugWindow] calling device_manager.SimulateTransponder(number, device)")
                self.device_manager.SimulateTransponder(int(number), int(device))
            else:
                raise AttributeError("DeviceManager has no simulate_transponder/SimulateTransponder method.")

            log("[DebugWindow] simulate_transponder OK")

        except Exception as e:
            log(f"[DebugWindow] simulate_transponder ERROR: {e}")
            QMessageBox.critical(self, "Debug", f"Unable to simulate transponder:\n{e}")