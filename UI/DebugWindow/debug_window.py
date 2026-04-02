from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget, QMessageBox

from Modules.log_utils import log
from UI.DebugWindow.debug_window_ui import DebugWindowUI

from Classes.race_list import RaceList


@dataclass
class _EnduranceEntry:
    team_label: str
    active_driver: object
    reserve_driver: Optional[object]


class DebugWindow(QDialog):
    """
    DebugWindow (simulate transponders)

    - Modalità normale:
        1 riga = 1 driver number
        pulsanti -> DeviceManager.simulate_transponder(number, device)  (ordine corretto)

    - Modalità endurance:
        1 riga = 1 team
        pulsanti standard usano SEMPRE il number del driver "active"
        pulsante SWAP scambia active <-> reserve (solo nella copia interna)
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        racelist: RaceList,
        device_manager: object,
        is_endurance: bool = False,
    ):
        super().__init__(parent)

        self.device_manager = device_manager
        self.is_endurance = bool(is_endurance)

        # Copia "shallow" dei driver: UI/Debug non deve toccare lo stato vero
        self._racelist_name = getattr(racelist, "name", "RaceList")

        self.drivers: List[object] = list(getattr(racelist, "drivers", []) or [])
        self.reserve_drivers: List[object] = list(getattr(racelist, "reserve_drivers", []) or [])
        self.roadsters = getattr(racelist, "roadsters", None)

        # Modalità endurance effettiva: parametro OR racelist.endurance_list
        self._endurance_mode = self.is_endurance or bool(getattr(racelist, "endurance_list", False))

        # IMPORTANT: teniamo references ai callback per evitare sorprese
        self._handlers: list[Callable[[], None]] = []

        # endurance: copia per entry (team + active/reserve)
        self._entries: list[_EnduranceEntry] = []

        log(f"[DEBUG_WIN] Avviato: lista='{self._racelist_name}' "
            f"piloti={len(self.drivers)} riserve={len(self.reserve_drivers)} "
            f"endurance={self._endurance_mode} device_manager={type(self.device_manager)}")

        self.ui = DebugWindowUI(self)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.addWidget(self.ui)

        self.setWindowTitle("E-Horizon • Debug")
        self.resize(980, 620)

        self._build_model()
        self.create_rows()

    # -----------------------
    # Helpers: driver fields
    # -----------------------
    @staticmethod
    def _get_number(d: object) -> Optional[int]:
        if d is None:
            return None
        n = getattr(d, "Number", None)
        if n is None:
            n = getattr(d, "number", None)
        if n is None:
            return None
        try:
            return int(n)
        except Exception:
            return None

    @staticmethod
    def _get_name_label(d: object) -> str:
        if d is None:
            return "-"
        label = getattr(d, "nameSurnameForResult", None)
        if label:
            return str(label)
        name = getattr(d, "name", "") or ""
        surname = getattr(d, "surname", "") or ""
        full = f"{name} {surname}".strip()
        return full if full else "Driver"

    @staticmethod
    def _get_team_label_from_driver(d: object) -> Optional[str]:
        if d is None:
            return None
        t = getattr(d, "team", None)
        if t is None:
            t = getattr(d, "Team", None)
        if t:
            return str(t)
        return None

    def _get_team_label(self, idx: int, main_driver: object) -> str:
        # 1) prova roadster.team / roadster.Team
        if self.roadsters and idx < len(self.roadsters):
            r = self.roadsters[idx]
            t = getattr(r, "team", None)
            if t is None:
                t = getattr(r, "Team", None)
            if t:
                return str(t)

        # 2) fallback su driver.team
        t2 = self._get_team_label_from_driver(main_driver)
        if t2:
            return t2

        # 3) fallback generico
        return f"{self._racelist_name} • TEAM {idx + 1}"

    # -----------------------
    # Model build
    # -----------------------
    def _build_model(self) -> None:
        self._entries.clear()

        if not self._endurance_mode:
            return

        # endurance: 1 entry per driver "main" (se c'è una reserve la mettiamo)
        for i, main in enumerate(self.drivers):
            reserve = self.reserve_drivers[i] if i < len(self.reserve_drivers) else None
            team_label = self._get_team_label(i, main)
            self._entries.append(_EnduranceEntry(team_label=team_label, active_driver=main, reserve_driver=reserve))

    # -----------------------
    # UI rows
    # -----------------------
    def create_rows(self) -> None:
        log("[DEBUG_WIN] Creazione righe UI avviata", level="DEBUG")
        self._handlers.clear()

        # pulizia UI
        self.ui.clear_rows()

        def callback_factory(device: int, number: int):
            #log(f"[DebugWindow] callback_factory(device={device}, number={number})")

            def handler():
                log(f"[DEBUG_WIN] Click transponder — device={device} numero={number}")
                self.send_udp_message(device=device, number=number)

            self._handlers.append(handler)
            return handler

        if not self._endurance_mode:
            # ----------------
            # Normal
            # ----------------
            numbers = [n for n in (self._get_number(d) for d in self.drivers) if n is not None]
            if not numbers:
                log("[DEBUG_WIN] Nessun pilota disponibile in modalità normale", level="WARN")
                self.ui.add_row("No drivers in RaceList", -1, lambda *_: (lambda: None))
                return

            for number in numbers:
                label = self._find_driver_label_by_number(int(number))
                self.ui.add_row(label, int(number), callback_factory)

            #log("[DebugWindow] create_rows() end (normal)")
            return

        # ----------------
        # Endurance
        # ----------------
        if not self._entries:
            log("[DEBUG_WIN] Nessuna entry disponibile in modalità endurance", level="WARN")
            self.ui.add_row("No endurance entries in RaceList", -1, lambda *_: (lambda: None))
            return

        for idx, e in enumerate(self._entries):
            active_num = self._get_number(e.active_driver)
            reserve_num = self._get_number(e.reserve_driver) if e.reserve_driver is not None else None

            active_label = (
                f"{self._get_name_label(e.active_driver)} (#{active_num:02d})"
                if active_num is not None else self._get_name_label(e.active_driver)
            )
            reserve_label = (
                f"{self._get_name_label(e.reserve_driver)} (#{reserve_num:02d})"
                if e.reserve_driver is not None and reserve_num is not None
                else (self._get_name_label(e.reserve_driver) if e.reserve_driver is not None else "-")
            )

            def make_swap_cb(i: int):
                def _swap():
                    self._swap_entry(i)
                    # ricrea bottoni così i callback puntano al nuovo number attivo
                    self.create_rows()
                return _swap

            swap_enabled = e.reserve_driver is not None and reserve_num is not None
            active_num_safe = int(active_num) if active_num is not None else -1

            self.ui.add_row_endurance(
                e.team_label,
                active_label,
                reserve_label,
                active_num_safe,
                callback_factory,
                make_swap_cb(idx),
                swap_enabled=swap_enabled,
            )

        log("[DEBUG_WIN] Creazione righe UI completata (endurance)", level="DEBUG")

    def _swap_entry(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._entries):
            return
        e = self._entries[idx]
        if e.reserve_driver is None:
            return
        e.active_driver, e.reserve_driver = e.reserve_driver, e.active_driver
        log(f"[DEBUG_WIN] Scambio piloti idx={idx} team='{e.team_label}' → attivo=#{self._get_number(e.active_driver)}")

    # -----------------------
    # Utilities
    # -----------------------
    def _find_driver_label_by_number(self, number: int) -> str:
        for d in self.drivers:
            n = self._get_number(d)
            if n is None:
                continue
            if int(n) == int(number):
                return self._get_name_label(d)
        return f"Driver #{number:02d}"

    def send_udp_message(self, *, device: int, number: int) -> None:
        log(f"[DEBUG_WIN] Invio transponder simulato — device={device} numero={number}", level="DEBUG")

        if device < 0 or device > 4:
            log("[DEBUG_WIN] Device fuori range (0..4) — ignorato", level="WARN")
            return

        if number < 0 or number > 99:
            log("[DEBUG_WIN] Numero fuori range (0..99) — avviso", level="WARN")
            QMessageBox.warning(self, "Debug", "Number must be between 0 and 99.")
            return

        try:
            # ✅ ORDINE CORRETTO: simulate_transponder(number, device)
            if hasattr(self.device_manager, "simulate_transponder"):
                log("[DEBUG_WIN] Chiamata simulate_transponder(numero, device)", level="DEBUG")
                self.device_manager.simulate_transponder(int(number), int(device))
            elif hasattr(self.device_manager, "SimulateTransponder"):
                log("[DEBUG_WIN] Chiamata SimulateTransponder(numero, device)", level="DEBUG")
                self.device_manager.SimulateTransponder(int(number), int(device))
            else:
                raise AttributeError("DeviceManager has no simulate_transponder/SimulateTransponder method.")

            log("[DEBUG_WIN] Simulazione transponder completata con successo", level="DEBUG")

        except Exception as e:
            log(f"[DEBUG_WIN] Errore simulazione transponder: {e}", level="ERROR")
            QMessageBox.critical(self, "Debug", f"Unable to simulate transponder:\n{e}")