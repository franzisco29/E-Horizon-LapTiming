from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot, QEvent
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidgetItem, QAbstractItemView, QHeaderView

from Modules.log_utils import log
from Modules.net import get_local_ipv4

from UI.RaceManagerWindow.race_manager_window_ui import build_race_manager_ui, RaceManagerWindowRefs
from UI.StatusWindow.status_window import StatusWindow

from Modules.db import Database, db_path_from_root, init_db
from Modules.repositories.drivers_repo import DriversRepo, DriverRow
from Modules.repositories.roadsters_repo import RoadstersRepo, RoadsterRow
from Modules.repositories.racelists_repo import RaceListsRepo, RaceListRow

from Classes.device_manager import DeviceManager, ConnectionTypes
from Modules.device_commands import DeviceCommand

from Modules.colors_utils import (
    GREEN_FLAG, YELLOW_FLAG, RED_FLAG, CLEAR_FLAG,
    set_pass_color, set_best_lap_cell, set_end
)
from UI.DebugWindow.debug_window import DebugWindow

from Classes.live_timing_hub import LiveTimingManager

from Classes.driver import Driver
from Classes.race_list import RaceList
from Classes.race_manager import RaceManager
from Classes.session import SessionState, SESSION_NAMES
from Modules.enums import RaceState
from Classes.roadster import Roadster

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

import traceback

import time
from time import perf_counter #to see
import threading



# ----------------------------
# Small helpers
# ----------------------------
@dataclass(slots=True)
class _LastSelection:
    pilot_key: Optional[str] = None


class RaceManagerWindow(QWidget):
    # Mandatory signals (per tua regola)
    sig_transponder = Signal(int, int)
    sig_status = Signal(list)
    sig_log = Signal(str)

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("RaceManager")

        # UI
        root, refs = build_race_manager_ui(self)
        self.refs: RaceManagerWindowRefs = refs

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(root)
        self.setLayout(lay)

        self.pit_open_val = 0
        # Core
        self.db: Optional[Database] = None
        self.drivers_repo: Optional[DriversRepo] = None
        self.roadsters_repo: Optional[RoadstersRepo] = None
        self.racelists_repo: Optional[RaceListsRepo] = None
        self._racelists_cache: List[RaceListRow] = []

        self.race_man: Optional[RaceManager] = None
        self.device_man: Optional[DeviceManager] = None
        self.live_man: Optional[LiveTimingManager] = None
        self.session_race_list: Optional[RaceList] = None

        # State
        self.yellows = [False, False, False]
        self.red_flag_out = False
        self.old_cmd: str = DeviceCommand.CLC_CMD.value
        self.old_pre_cmd: str = DeviceCommand.PRE_RACE_CMD.value
        self._last_sel = _LastSelection()

        # Timers
        self._ses_timer = QTimer(self)
        self._ses_timer.setInterval(1000)
        self._ses_timer.timeout.connect(self._on_session_tick)

        self._pos_timer = QTimer(self)
        self._pos_timer.setInterval(1000)
        self._pos_timer.timeout.connect(self._on_pos_tick)

        self._pre_timer = QTimer(self)
        self._pre_timer.setInterval(1000)
        self._pre_timer.timeout.connect(self._on_pre_race_tick)

        # Startup status polling (no freeze)
        self._startup_win: Optional[StatusWindow] = None
        self._startup_timer: Optional[QTimer] = None

        # Init
        log("RaceManagerWindow: init() start")
        self._setup_table()
        self._bind_signals()
        self._bind_ui()
        self._init_db()
        self._populate_session_box()
        self._admin_setup()
        self._build_racelists_cache()
        
        endurance = bool(self.race_man.endurance) if self.race_man else False
        self._fill_racelists_combo(endurance)
        self._old_endurance = endurance
        
        self._apply_debug_visibility()
        self._enable_idle_state()
        log("RaceManagerWindow: init() done")

    # ------------------------------------------------------------
    # UI/table setup -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    def _setup_table(self) -> None:
        t = self.refs.lap_table

        # no user sorting/editing
        t.setSortingEnabled(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.verticalHeader().setVisible(False)
        t.setWordWrap(False)

        # ✅ VINCOLO: NO SCROLL ORIZZONTALE, tabella sempre intera
        t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setSectionsMovable(False)
        t.horizontalHeader().setHighlightSections(False)
        
        self.setup_laptimingtable()
        log("Table setup done (VB columns, no H-scroll)")

    def _apply_debug_visibility(self) -> None:
        # settings.debug può essere bool o int
        dbg = getattr(self.settings, "debug", False)
        self.refs.debug_btn.setVisible(bool(dbg))
        log(f"[RaceWindow] Debug button visible={bool(dbg)}")

    def _enable_idle_state(self) -> None:
        # come VB: dopo startup, puoi caricare lista; start/stop solo dopo load
        self.refs.start_btn.setEnabled(False)
        self.refs.reset_btn.setEnabled(False)
        self.refs.save_results_btn.setEnabled(False)
        self.refs.pre_race_btn.setEnabled(False)
        self.refs.apply_status_btn.setEnabled(False)

    # ------------------------------------------------------------
    # Signals (device -> UI thread safe) -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    def _bind_signals(self) -> None:
        self.sig_transponder.connect(self._on_transponder_gui_thread)
        self.sig_log.connect(self._on_log_gui_thread)

    @Slot(str)
    def _on_log_gui_thread(self, msg: str) -> None:
        log(f"[RaceWindow] [Device] {msg}")

    # ------------------------------------------------------------
    # UI bindings -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    def _bind_ui(self) -> None:
        r = self.refs

        r.load_btn.clicked.connect(self._on_load_clicked)
        r.start_btn.clicked.connect(self._on_start_clicked)
        r.reset_btn.clicked.connect(self._on_reset_clicked)
        r.save_results_btn.clicked.connect(self._on_save_results_clicked)
        r.debug_btn.clicked.connect(self._on_debug_clicked)

        r.pre_race_btn.clicked.connect(self._on_pre_race_clicked)
        r.apply_status_btn.clicked.connect(self._on_apply_status_clicked)

        # flags
        r.ys1_btn.clicked.connect(lambda: self._toggle_yellow(0))
        r.ys2_btn.clicked.connect(lambda: self._toggle_yellow(1))
        r.ys3_btn.clicked.connect(lambda: self._toggle_yellow(2))
        r.sc_btn.clicked.connect(self._on_sc_clicked)
        r.vsc_btn.clicked.connect(self._on_vsc_clicked)
        r.green_btn.clicked.connect(self._on_green_clicked)
        r.red_btn.clicked.connect(self._on_red_clicked)
        r.clear_btn.clicked.connect(self._on_clear_clicked)
        r.wet_btn.clicked.connect(self._on_wet_clicked)
        r.formation_btn.clicked.connect(self._on_formation_lap_clicked)
        r.op_pit_btn.clicked.connect(self._on_open_pit_clicked)
        r.cl_pit_btn.clicked.connect(self._on_close_pit_clicked)

        r.session_box.currentIndexChanged.connect(self._on_session_type_changed)

    # ------------------------------------------------------------
    # DB -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    def _init_db(self) -> None:
        root_path = getattr(getattr(self.settings, "paths", None), "root_path", None) or getattr(self.settings, "root_path", None)
        if not root_path:
            raise ValueError("Missing settings.paths.root_path (or root_path)")

        db_path = db_path_from_root(str(root_path), filename="ehorizon.db")
        self.db = Database(db_path)
        init_db(self.db)

        self.drivers_repo = DriversRepo(self.db)
        self.roadsters_repo = RoadstersRepo(self.db)
        self.racelists_repo = RaceListsRepo(self.db)

        log(f"[RaceWindow] DB init ok: {db_path}")

    def _refresh_racelists_combo(self) -> None:
        if not self.racelists_repo:
            return
        self._racelists_cache = self.racelists_repo.list_all()
        box = self.refs.racelist_box
        box.blockSignals(True)
        box.clear()
        for row in self._racelists_cache:
            box.addItem(row.display(), row.list_id)
        box.blockSignals(False)
        if box.count() > 0:
            box.setCurrentIndex(0)
        log(f"[RaceWindow] RaceLists loaded in combo: {len(self._racelists_cache)}")

    def _selected_list_id(self) -> int:
        lid = self.refs.racelist_box.currentData()
        return int(lid) if lid is not None else 0

    def _build_racelists_cache(self) -> None:
        """Carica tutte le racelists UNA volta e crea due viste (endur/non-endur)."""
        if not self.racelists_repo:
            self._racelists_all = []
            self._racelists_by_endurance = {False: [], True: []}
            return

        self._racelists_all = self.racelists_repo.list_all()

        by_end = {False: [], True: []}
        for row in self._racelists_all:
            by_end[bool(row.is_endurance)].append(row)

        self._racelists_by_endurance = by_end
        
    def _fill_racelists_combo(self, endurance: bool) -> None:
        rows = self._racelists_by_endurance.get(bool(endurance), [])
        box = self.refs.racelist_box

        box.blockSignals(True)
        box.clear()
        for row in rows:
            box.addItem(row.display(), row.list_id)
        box.blockSignals(False)

        if box.count() > 0:
            box.setCurrentIndex(0)

        log(f"[RaceWindow] RaceLists combo filled endurance={endurance}: {len(rows)}")
        
    # ------------------------------------------------------------
    # Populate session box (VB indices) -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    def _populate_session_box(self) -> None:
        box = self.refs.session_box
        box.blockSignals(True)
        box.clear()
        box.addItems(SESSION_NAMES)
        box.setCurrentIndex(0)
        box.blockSignals(False)
        log("SessionBox populated")

    # ------------------------------------------------------------
    # Admin setup (Live + Device) - NO freeze - OK DO NOT TOUCH
    # ------------------------------------------------------------
    def _admin_setup(self) -> None:
        # RaceManager init (compat per firme diverse)
        debounce_ms = self.settings.debounce_ms
        log(f"[RaceWindow] {debounce_ms}")
        try:
            self.race_man = RaceManager(0, debounce_ms)
        except TypeError:
            self.race_man = RaceManager(session_type=0, debounce_ms=debounce_ms)
            
        self.race_man.logger = log

        self.live_man = None

        if self.settings.live_enabled:
            live_ip = self.settings.live_ip
            live_port = self.settings.live_port

            self.live_man = LiveTimingManager(live_ip, live_port, root_path=self.settings.root_path)
            self.live_man.start()

            log(f"[RaceWindow] LiveTiming started on {live_ip}:{live_port} (WEB on {live_port + 1})")
        else:
            log("[RaceWindow] LiveTiming disabled by settings")

        # DeviceManager
        ip = self._get_local_ip_best_effort()
        tcp_port = int(getattr(getattr(self.settings, "devices", None), "tcp_port", 20777))
        conn_type = int(getattr(getattr(self.settings, "devices", None), "connection_type", 0))
        flags_raw = str(getattr(getattr(self.settings, "devices", None), "device_available", "1,1,1,1,1,1"))
        active_flags = self._parse_active_flags(flags_raw)

        log(f"[RaceWindow] DeviceManager config: IP={ip} PORT={tcp_port} ConnType={conn_type} Flags={active_flags}")

        self.device_man = DeviceManager(ip, tcp_port, conn_type, active_flags)
        self.device_man.on_log = self._cb_log
        self.device_man.on_transponder_received_index = self._cb_transponder
        type(self.device_man).add_transponder_simulated_index_listener(self._cb_transponder)

        # UI session info
        self.refs.ip_label.setText(ip if conn_type != ConnectionTypes.NONE else "NONE")

        # Startup window only if not NONE
        if self.device_man.conn_type == ConnectionTypes.NONE:
            log("Startup: ConnectionTypes.NONE -> skip polling")
            return

        self._startup_win = StatusWindow(self)
        self._startup_win.show()
        self._startup_win.update_connection(self.device_man.ip, int(self.device_man.port))

        self._startup_timer = QTimer(self)
        self._startup_timer.setInterval(200)
        self._startup_timer.timeout.connect(self._poll_startup)
        self._startup_timer.start()

    def _poll_startup(self) -> None:
        if not self.device_man or not self._startup_win:
            return

        if self._startup_win.startup_cancelled:
            log("Startup cancelled -> closing window")
            self.close()
            return

        self._startup_win.update_status(self.device_man.get_device_status_list())

        if self.device_man.all_required_devices_connected():
            log("Startup: all devices connected")
            if self._startup_timer:
                self._startup_timer.stop()
                self._startup_timer = None
            self._startup_win.close()
            self._startup_win = None

    # ------------------------------------------------------------
    # Device callbacks -> signals -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    def _cb_log(self, msg: str) -> None:
        self.sig_log.emit(str(msg))

    def _cb_transponder(self, device_id: int, number: int) -> None:
        self.sig_transponder.emit(int(device_id), int(number))

    # ------------------------------------------------------------
    # LOAD (DB -> RaceList -> Table) -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    @Slot()
    def _on_load_clicked(self) -> None:
        if not (self.race_man and self.racelists_repo and self.drivers_repo and self.roadsters_repo):
            log("LOAD: missing components")
            return

        list_id = self._selected_list_id()
        log(f"[RaceWindow]  LOAD click: list_id={list_id} text='{self.refs.racelist_box.currentText()}'")

        try:
            self.session_race_list = self._load_racelist_from_db(list_id)
        except Exception as e:
            log(f"[RaceWindow]  LOAD FAILED: {e}")
            return

        self.race_man.session_race_list = self.session_race_list
        self.write_lap_timing(self.session_race_list)

        # enable like VB
        self.refs.start_btn.setEnabled(True)
        self.refs.reset_btn.setEnabled(True)
        self.refs.save_results_btn.setEnabled(True)
        self.refs.pre_race_btn.setEnabled(True)
        self.refs.apply_status_btn.setEnabled(True)

        # update header info
        self.refs.session_value.setText(self.refs.session_box.currentText())
        self.refs.pit_label.setText("Pit Closed")
        self.refs.timer_value.setText(self._format_mmss(getattr(self.race_man, "session_time", 0)))

        if self.live_man and self.live_man.enabled:
            self.live_man.send_session_info(self.race_man)
            self.live_man.send_race_data(self.session_race_list.drivers)

        log(f"[RaceWindow]  LOAD OK: endurance={getattr(self.session_race_list,'endurance_list',False)} drivers={len(self.session_race_list.drivers)}")

    def _load_racelist_from_db(self, list_id: int) -> RaceList:
        assert self.racelists_repo and self.drivers_repo and self.roadsters_repo

        meta = self.racelists_repo.get(list_id)
        if not meta:
            raise ValueError(f"RaceList not found id={list_id}")

        all_drivers: Dict[int, DriverRow] = {d.driver_id: d for d in self.drivers_repo.get_all()}

        # -------------------------
        # NON endurance
        # -------------------------
        if not meta.is_endurance:
            ids = self.racelists_repo.get_driver_ids(meta.list_id)
            drivers: List[Driver] = []
            for did in ids:
                r = all_drivers.get(did)
                if not r:
                    continue
                drivers.append(self._driver_from_row(r))

            return RaceList(
                name=meta.name,
                drivers=drivers,
                roadsters=None,
                endurance_list=False,
            )

        # -------------------------
        # endurance
        # -------------------------
        roadster_ids = self.racelists_repo.get_roadster_ids(meta.list_id)

        all_rs = self.roadsters_repo.list_all()
        by_id: Dict[int, RoadsterRow] = {r.roadster_id: r for r in all_rs}

        roadsters: List[Roadster] = []

        for rid in roadster_ids:
            rs = by_id.get(rid)
            if not rs:
                continue

            d1_row = all_drivers.get(rs.driver1_id)
            d2_row = all_drivers.get(rs.driver2_id)
            if not d1_row or not d2_row:
                continue

            d1 = self._driver_from_row(d1_row)
            d2 = self._driver_from_row(d2_row)

            # ✅ oggetto runtime, non tuple
            rd = Roadster(first_driver=d1, second_driver=d2)
            # opzionale: se vuoi preservare il team dal DB anche se driver.team è vuoto
            if getattr(rs, "team", None):
                rd.team = rs.team

            roadsters.append(rd)

        return RaceList(
            name=meta.name,
            roadsters=roadsters,
            endurance_list=True,
        )

    def _driver_from_row(self, r: DriverRow) -> Driver:
        return Driver(
            driver_id=int(r.driver_id),
            name=str(r.name),
            surname=str(r.surname),
            number=int(r.transponder_id),
            team=str(r.team),
            pro=bool(r.pro),
            race_number=int(r.race_number),
        )

    # ------------------------------------------------------------
    # WRITE TABLE (VB columns) + elision Pilota/Team -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    def write_lap_timing(self, race_list: RaceList) -> None:
        t = self.refs.lap_table
        t.setRowCount(0)

        fm = QFontMetrics(t.font())

        def elide(text: str, px: int) -> str:
            return fm.elidedText(text, Qt.ElideRight, px)

        for d in race_list.drivers:
            row = d.to_lap_timing()
            # row:
            # [0 pos, 1 name, 2 team, 3 s1,4 s2,5 s3,
            #  6 last, 7 laps, 8 status, 9 gap,
            #  10 interval, 11 fast, 12 total]

            pilot_full = row[1]
            team_full = row[2]

            # Elide solo per UI
            row[1] = elide(pilot_full, 260)
            row[2] = elide(team_full, 220)

            r = t.rowCount()
            t.insertRow(r)

            for c, val in enumerate(row):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(
                    int(Qt.AlignVCenter | (Qt.AlignLeft if c in (1, 2) else Qt.AlignHCenter))
                )

                if c == 1:
                    it.setToolTip(pilot_full)
                elif c == 2:
                    it.setToolTip(team_full)

                t.setItem(r, c, it)

            # End-of-race coloring
            rs = getattr(d, "race_status", 0)
            try:
                rs_i = int(rs)
            except Exception:
                rs_i = 0

            if rs_i == 2 or rs_i > 4:
                set_end(t, r)

        log(f"[RaceWindow]  write_lap_timing: rows={t.rowCount()}")
        
    def _capture_selection_pilot_key(self) -> Optional[str]:
        """
        VB: selectedID = LapTimingView.Rows(id_row).Cells(1).Value
        In Qt: prendiamo tooltip della colonna Pilota (1) se presente, altrimenti text.
        """
        t = self.refs.lap_table
        sel = t.selectedItems()
        if not sel:
            return None
        row = sel[0].row()
        it = t.item(row, 1)  # colonna Pilota
        if not it:
            return None
        tip = (it.toolTip() or "").strip()
        return tip if tip else (it.text() or "").strip()

    def _restore_selection_by_pilot_key(self, pilot_key: Optional[str]) -> None:
        """VB: RestoreSelection(laptimingview, selectedID)"""
        if not pilot_key:
            return

        t = self.refs.lap_table
        for r in range(t.rowCount()):
            it = t.item(r, 1)
            if not it:
                continue
            tip = (it.toolTip() or "").strip()
            txt = (it.text() or "").strip()
            if pilot_key == (tip if tip else txt):
                t.selectRow(r)
                t.scrollToItem(it)  # comodo come “restore focus”
                return

    def _update_gui_after_pass(self, lista: RaceList, idx: int, best_idx: int, swap: bool, lap_state: int) -> None:
        """
        Porting VB UpdateGUI(...)
        - writeLapTiming
        - setPassColor (se status ok + lap_state ok)
        - LiveMan.SendRaceData(drivers) (solo se lap_state ok)
        - LiveMan.SendEvent(...) (solo se lap_state ok)
        - setBestLapCell
        """
        # 1) writeLapTiming(laptimingview, lista)
        self.write_lap_timing(lista)

        # Guard: idx valido
        if idx is None or idx < 0 or idx >= len(lista.drivers):
            log(f"[RaceWindow] _update_gui_after_pass: invalid idx={idx} drivers={len(lista.drivers)}")
            return

        # VB: if Race_status <> 2 and < 5 then setPassColor(...)
        try:
            rs = int(getattr(lista.drivers[idx], "race_status", 0))
        except Exception:
            rs = 0

        # Consideriamo "pass valido" solo se lap_state > 0
        pass_valid = (lap_state is not None and int(lap_state) > 0)

        # 2) set_pass_color (solo se non ended e pass valido)
        if rs != 2 and rs < 5 and pass_valid:
            try:
                set_pass_color(self.refs.lap_table, idx, swap, best_idx, lap_state)
            except Exception as e:
                log(f"[RaceWindow] set_pass_color ERROR: {e}")

        # 3) Live: aggiorna lista drivers + flash evento (solo se pass valido e driver non ended)
        if pass_valid and rs != 2 and rs < 5:
            # VB: LiveMan.SendRaceData(drivers)
            try:
                if self.live_man and self.live_man.enabled:
                    self.live_man.send_race_data(lista.drivers)
            except Exception as e:
                log(f"[RaceWindow] send_race_data ERROR: {e}")

            # Flash evento
            try:
                if self.live_man and self.live_man.enabled:
                    kind = "swap" if swap else ("pole" if idx == 0 else "passed")
                    d = lista.drivers[idx]
                    key = getattr(d, "number", None) or getattr(d, "driver_id", idx) or idx
                    self.live_man.send_event(key, kind)
            except Exception as e:
                log(f"[RaceWindow] send_event ERROR: {e}")

        # 4) setBestLapCell (anche se il pass era debounce può comunque esistere un best_idx aggiornato,
        # ma in genere best_idx cambia su pass valido: lo lasciamo comunque come prima)
        if best_idx is not None and best_idx >= 0 and best_idx != idx:
            try:
                set_best_lap_cell(self.refs.lap_table, best_idx)
            except Exception as e:
                log(f"[RaceWindow] set_best_lap_cell ERROR: {e}")
    # ------------------------------------------------------------
    # Session type change & Swap -- OK DO NOT TOUCH
    # ------------------------------------------------------------

    def swap_best_and_last_lap(self, table: QTableWidget, race: bool, endurance: bool) -> None:
        header = table.horizontalHeader()
        header.setSectionsMovable(True)

        def set_display_index(logical_col: int, display_index: int) -> None:
            current_visual = header.visualIndex(logical_col)
            if current_visual != display_index:
                header.moveSection(current_visual, display_index)

        def set_header_text(logical_col: int, text: str) -> None:
            item = table.horizontalHeaderItem(logical_col)
            if item is None:
                table.setHorizontalHeaderItem(logical_col, QTableWidgetItem(text))
            else:
                item.setText(text)

        if race:
            if endurance:
                set_display_index(1, 2)
                set_display_index(2, 1)
                set_header_text(1, "Pilota Corrente")
            else:
                set_display_index(1, 1)
                set_display_index(2, 2)
                set_header_text(1, "Pilota")

            set_display_index(6, 6)
            set_display_index(11, 11)
        else:
            set_display_index(6, 11)
            set_display_index(11, 6)

    @Slot(int)
    def _on_session_type_changed(self, idx: int) -> None:
        if not self.race_man:
            return

        # Aggiorna il tipo sessione nel model (Session)
        self.race_man.session_type = int(idx)

        # qui decidi race/endurance (usa le tue property reali)
        race = self.race_man.race
        endurance = self.race_man.endurance
        
        # VB: If old_endurace <> raceMan.Endurance Then ...
        if self._old_endurance is None:
            self._old_endurance = bool(endurance)

        if bool(endurance) != bool(self._old_endurance):
            log(f"[RaceWindow] Endurance changed: {self._old_endurance} -> {endurance}")

            # Clear UI like VB
            self.refs.racelist_box.blockSignals(True)
            self.refs.racelist_box.clear()
            self.refs.racelist_box.blockSignals(False)

            self.refs.lap_table.setRowCount(0)

            # Reset current loaded list
            self.session_race_list = None
            try:
                self.race_man.session_race_list = None
            except Exception:
                pass

            # Fill combo using cache (no DB calls)
            self._fill_racelists_combo(bool(endurance))

            # Update state
            self._old_endurance = bool(endurance)

            # Optional: disable start until LOAD
            self._enable_idle_state()

        # swap colonne SOLO grafico
        self.swap_best_and_last_lap(self.refs.lap_table, race=race, endurance=endurance)

        log(f"[RaceWindow]  is race? {race} endurance? {endurance}")

        # Prendi il tempo max dal race_man (Session.max_session_time)
        max_sec = int(self.race_man.session.max_session_time[int(idx)])

        # Resetta il timer della sessione
        self.race_man.session_time = max_sec

        # Aggiorna UI
        self.refs.session_value.setText(self.race_man.get_session_name())
        self.refs.timer_value.setText(self.race_man.session.session_timer_mmss())

    # ------------------------------------------------------------
    # START/STOP (base, poi completiamo 1:1 VB step successivo) -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    
    @Slot()
    def _on_start_clicked(self) -> None:
        # VB: PreRaceTimer.Stop()
        self._pre_timer.stop()

        if not (self.race_man and self.device_man):
            return

        act_state = getattr(self.race_man, "session_status", SessionState.NotStarted)
        try:
            act_state = SessionState(act_state)
        except Exception:
            pass

        log(f"[RaceWindow]  Start click: status={act_state}")

        # Helpers
        def _disable_combos(disabled: bool) -> None:
            self.refs.session_box.setEnabled(not disabled)
            self.refs.racelist_box.setEnabled(not disabled)

        def _refresh_table() -> None:
            if self.session_race_list:
                self.write_lap_timing(self.session_race_list)

        # ------------------------------------------------------------
        # NOT STARTED  (VB NotStarted)
        # ------------------------------------------------------------
        if act_state == SessionState.NotStarted:
            _disable_combos(True)

            # VB: raceMan.StartSession()
            self.race_man.start_session()

            # VB: StartBT.Text = "Stop"
            self.refs.start_btn.setText("Stop")

            # VB: SesTimer.Start()
            self._ses_timer.start()

            # VB: raceMan.SectorsOn = DeviceMan.CheckSectorsDevices
            # VB: raceMan.PitOn = DeviceMan.CheckPitDevices
            # Nel tuo Python non vedo ancora questi metodi: metto tentativo + fallback.
            try:
                self.race_man.session.sectors_on = bool(getattr(self.device_man, "check_sectors_devices")())
            except Exception:
                try:
                    self.race_man.session.sectors_on = bool(getattr(self.device_man, "CheckSectorsDevices")())
                except Exception:
                    pass

            try:
                self.race_man.session.pit_on = bool(getattr(self.device_man, "check_pit_devices")())
            except Exception:
                try:
                    self.race_man.session.pit_on = bool(getattr(self.device_man, "CheckPitDevices")())
                except Exception:
                    pass

            # VB: lista = raceMan.SessionRaceList + writeLapTiming
            _refresh_table()

            # VB: DeviceMan.Broadcast(DeviceCommand.START_CMD)
            self.device_man.broadcast(DeviceCommand.START_CMD.value)

            # VB: posTimer.Start()
            self._pos_timer.start()

            # VB: ResultBT.Enabled = True
            self.refs.save_results_btn.setEnabled(True)

            log("Session STARTED")

        # ------------------------------------------------------------
        # STARTED  (VB Started)
        # ------------------------------------------------------------
        elif act_state == SessionState.Started:
            _disable_combos(True)

            # VB: raceMan.StopSession()
            self.race_man.stop_session()

            # VB: StartBT.Text = "Continue"
            self.refs.start_btn.setText("Continue")

            # VB: If raceMan.SessionType > 0 Then SesTimer.Stop()
            # In Python, session_type sta in race_man.session.session_type
            try:
                sess_type = int(self.race_man.session.session_type)
            except Exception:
                sess_type = int(getattr(self.race_man, "session_type", 0) or 0)

            if sess_type > 0:
                self._ses_timer.stop()

            # VB: If Not redFlagOut Then ControlPitLaneOpen()
            # Nel Python non vedo ControlPitLaneOpen(): metto TODO se non esiste.
            if not self.red_flag_out:
                if hasattr(self, "control_pit_lane_open"):
                    try:
                        self.control_pit_lane_open()
                    except Exception as e:
                        log(f"[RaceWindow]  control_pit_lane_open() error: {e}")
                else:
                    # TODO: portare ControlPitLaneOpen dal VB
                    pass

            # VB: posTimer.Stop()
            self._pos_timer.stop()

            # VB: PitStateLB.Text = "Pit Closed"
            self.refs.pit_label.setText("Pit Closed")

            # VB: writeLapTiming
            _refresh_table()

            # VB: DeviceMan.Broadcast(DeviceCommand.RED_FLAG_CMD)
            self.device_man.broadcast(DeviceCommand.RED_FLAG_CMD.value)

            log("Session STOPPED")

        # ------------------------------------------------------------
        # FINISHED  (VB Finished)
        # ------------------------------------------------------------
        elif act_state == SessionState.Finished:
            _disable_combos(False)

            # VB: raceMan.ResetSession()
            self.race_man.reset_session()

            # VB: PitStateLB.Text = "Pit Closed"
            self.refs.pit_label.setText("Pit Closed")

            # VB: StartBT.Text = "Start"
            self.refs.start_btn.setText("Start")

            # VB: LapTimingView.Rows.Clear() + writeLapTiming
            # (noi riscriviamo tabella da lista: è equivalente)
            _refresh_table()

            # VB: ControlPitLaneOpen()
            if hasattr(self, "control_pit_lane_open"):
                try:
                    self.control_pit_lane_open()
                except Exception as e:
                    log(f"[RaceWindow] control_pit_lane_open() error: {e}")

            # VB: posTimer.Stop()
            self._pos_timer.stop()

            log("Session RESET (from Finished)")

        # ------------------------------------------------------------
        # STARTING  (VB Starting)  -> pre-race semaforo / start procedure
        # ------------------------------------------------------------
        elif act_state == SessionState.Starting:
            # VB: DeviceMan.SendCommand(DeviceCommand.START_PROC_CMD, Sem)
            # Nel tuo DeviceCommand non vedo START_PROC: se esiste con altro nome, mappalo.

            self.device_man.send_command(DeviceCommand.START_PROC_CMD.value, DeviceManager.DevicesIDs.Sem)  # type: ignore


            # VB: StartBT.Text = "Lights Out"
            self.refs.start_btn.setText("Lights Out")

            # VB: raceMan.SessionStatus = 0  (NotStarted)
            try:
                self.race_man.session_status = int(SessionState.NotStarted)
            except Exception:
                pass

            log("Session STARTING -> Lights Out")

        # ------------------------------------------------------------
        # STOPPED  (VB Stopped)
        # ------------------------------------------------------------
        elif act_state == SessionState.Stopped:
            # VB: redFlagOut = False
            self.red_flag_out = False

            # VB: StartBT.Text = "Stop"
            self.refs.start_btn.setText("Stop")

            # VB: If raceMan.SessionType > 0 Then SesTimer.Start()
            try:
                sess_type = int(self.race_man.session.session_type)
            except Exception:
                sess_type = int(getattr(self.race_man, "session_type", 0) or 0)

            if sess_type > 0:
                self._ses_timer.start()

            # VB: raceMan.ResumeSession()
            self.race_man.resume_session()

            # VB: SectorsOn / PitOn aggiornati
            try:
                self.race_man.session.sectors_on = bool(getattr(self.device_man, "check_sectors_devices")())
            except Exception:
                try:
                    self.race_man.session.sectors_on = bool(getattr(self.device_man, "CheckSectorsDevices")())
                except Exception:
                    pass

            try:
                self.race_man.session.pit_on = bool(getattr(self.device_man, "check_pit_devices")())
            except Exception:
                try:
                    self.race_man.session.pit_on = bool(getattr(self.device_man, "checkPitDevices")())
                except Exception:
                    pass

            # VB: writeLapTiming + ControlPitLaneOpen
            _refresh_table()

            if hasattr(self, "control_pit_lane_open"):
                try:
                    self.control_pit_lane_open()
                except Exception as e:
                    log(f"[RaceWindow] control_pit_lane_open() error: {e}")

            # VB: posTimer.Stop()   (sì, nel VB è Stop qui)
            self._pos_timer.stop()

            # VB: Broadcast GREEN
            self.device_man.broadcast(DeviceCommand.GREEN_FLAG_CMD.value)

            log("Session RESUMED")

        # sync live (uguale al tuo)
        if self.live_man and self.live_man.enabled:
            self.live_man.send_session_info(self.race_man)
    
    # ------------------------------------------------------------
    # RESET TO IMPLEMENT BETTER
    # ------------------------------------------------------------
    
    @Slot()
    def _on_reset_clicked(self) -> None:
        if not self.race_man:
            return
        self._ses_timer.stop()
        self._pos_timer.stop()
        self._pre_timer.stop()
        self.race_man.reset_session()
        self.refs.start_btn.setText("Start")
        self.refs.timer_value.setText("00:00")
        self.refs.pit_label.setText("Pit Closed")
        log("Session RESET")

    # ------------------------------------------------------------
    # Timers ticks -- OK DO NOT TOUCH
    # ------------------------------------------------------------
    
    def _on_session_tick(self) -> None:
        if not self.race_man:
            return

        rm = self.race_man

        # --- tempo residuo ---
        tleft = int(getattr(rm, "session_time", 0) or 0)

        # VB: If raceMan.SessionTime = 0 Then ...
        if tleft <= 0:
            try:
                rm.session_time = 0
            except Exception:
                pass
            
            if not self.race_man.time_over:
                self.race_man.time_over = True

            self.refs.timer_value.setText("00:00")

            # VB: raceMan.EndSession()
            try:
                rm.end_session()
            except Exception as e:
                log(f"[RaceWindow] end_session() ERROR: {e}")

            # VB: DeviceMan.SendCommand(END_SESSION_CMD, Sem)
            try:
                if self.device_man:
                    self.device_man.send_command(DeviceCommand.END_SESSION_CMD, DeviceManager.DevicesIDs.Sem)  
            except Exception as e:
                log(f"[RaceWindow] send END_SESSION_CMD ERROR: {e}")

            # VB: If raceMan.allEnded() Then ...
            try:
                all_ended = bool(rm.all_ended())
            except Exception:
                all_ended = True  # fallback: se non hai ancora all_ended, chiudiamo lo stesso

            if all_ended:
                try:
                    self._ses_timer.stop()
                except Exception:
                    pass

                # VB UI reset
                try:
                    self.refs.start_btn.setText("Reset")
                    self.refs.session_box.setEnabled(True)
                    self.refs.racelist_box.setEnabled(True)
                    self.refs.pit_label.setText("Pit Closed")
                except Exception:
                    pass

                # VB: chiude pit se era aperta
                try:
                    if getattr(self, "pit_open_val", 0) != 0:
                        self.control_pit_lane_open()
                        self.pit_open_val = 0
                except Exception:
                    pass

            # invio live session info anche a sessione finita (ok)
            try:
                if self.live_man and self.live_man.enabled:
                    self.live_man.send_session_info(rm)
            except Exception:
                pass

            # Invia anche i dati finali dei piloti alla pagina web
            try:
                if self.live_man and self.live_man.enabled and self.session_race_list:
                    self.live_man.send_race_data(self.session_race_list.drivers)
            except Exception as e:
                log(f"[RaceWindow] send_race_data (finish) ERROR: {e}")

            return

        # --- tick normale: decrementa ---
        tleft -= 1
        try:
            rm.session_time = tleft
        except Exception:
            pass

        self.refs.timer_value.setText(self._format_mmss(tleft))

        try:
            pit_state = rm.pit_state
            #log(f"[RaceWindow] PIT tick -> pit_state={pit_state}")
        except Exception as e:
            #log(f"[RaceWindow] PIT tick -> ERROR reading pit_state: {e}")
            pit_state = 0

        if pit_state != 0:
            try:
                is_valid = bool(rm.open_pit())
                #log(f"[RaceWindow] PIT open_pit() -> {is_valid}")
            except Exception as e:
                log(f"[RaceWindow] PIT open_pit() ERROR: {e}")
                is_valid = False

            if is_valid:
                self.refs.pit_label.setText("Pit VALID")

                if getattr(self, "pit_open_val", 0) != 2:
                    #log("[RaceWindow] PIT -> sending VALID state to device")
                    try:
                        self.control_pit_lane_open()
                    except Exception as e:
                        log(f"[RaceWindow] control_pit_lane_open ERROR: {e}")
                    self.pit_open_val = 2
                #else:
                    #log("[RaceWindow] PIT already in VALID state, no command sent")

            else:
                self.refs.pit_label.setText("Pit Open")

                if getattr(self, "pit_open_val", 0) != 1:
                    #log("[RaceWindow] PIT -> sending OPEN state to device")
                    try:
                        self.control_pit_lane_open()
                    except Exception as e:
                        log(f"[RaceWindow] control_pit_lane_open ERROR: {e}")
                    self.pit_open_val = 1
                #else:
                    #log("[RaceWindow] PIT already in OPEN state, no command sent")

        else:
            #log("[RaceWindow] PIT state = 0 (CLOSED) -> forcing device sync")
            try:
                self.control_pit_lane_open()
            except Exception as e:
                log(f"[RaceWindow] control_pit_lane_open ERROR: {e}")
                
        # -------------------------
        # Flags / lights (se esiste)
        # -------------------------
        try:
            self.set_flag(getattr(self, "old_cmd", None))
        except Exception:
            pass

        # -------------------------
        # Live session info via WS
        # -------------------------
        try:
            if self.live_man and self.live_man.enabled:
                self.live_man.send_session_info(rm)
        except Exception:
            pass

    def _on_pos_tick(self) -> None:
        if self.race_man:
            try:
                self.race_man.save_position()
            except Exception:
                pass

    # ------------------------------------------------------------
    # Pre-race (base + log; poi lo portiamo 1:1 VB nel prossimo step)
    # ------------------------------------------------------------
    @Slot()
    def _on_pre_race_clicked(self) -> None:
        if not (self.race_man and self.device_man):
            return
        minutes = int(self.refs.pre_race_minutes_box.currentText())
        sec = minutes * 60
        try:
            self.race_man.pre_race_time = sec
        except Exception:
            try:
                self.race_man.session.pre_race_time = sec
            except Exception:
                pass
        self._pre_timer.start()
        self.device_man.send_command(DeviceCommand.PRE_RACE_CMD.value, DeviceManager.DevicesIDs.Sem)
        self.old_pre_cmd = DeviceCommand.PRE_RACE_CMD.value
        log(f"[RaceWindow] Pre-race START: {minutes}min")

    def _on_pre_race_tick(self) -> None:
        if not (self.race_man and self.device_man):
            return
        try:
            sec = int(getattr(self.race_man, "pre_race_time"))
            sec -= 1
            self.race_man.pre_race_time = sec
        except Exception:
            sec = int(getattr(getattr(self.race_man, "session", None), "pre_race_time", 0)) - 1
            try:
                self.race_man.session.pre_race_time = sec
            except Exception:
                pass

        # mostra countdown su timer
        self.refs.timer_value.setText(self._format_mmss(sec))

        # command thresholds (PRE10/PRE5/PRE2/PRE1)
        cmd = self._pre_race_command(sec)
        if cmd != self.old_pre_cmd:
            self.device_man.send_command(cmd, DeviceManager.DevicesIDs.Sem)
            log(f"[RaceWindow] Pre-race CMD change: {self.old_pre_cmd} -> {cmd} at {self._format_mmss(sec)}")
            self.old_pre_cmd = cmd

        if sec <= 0:
            self._pre_timer.stop()
            log("Pre-race END")

    def _pre_race_command(self, sec_left: int) -> str:
        if sec_left <= 60:
            return DeviceCommand.PRE1_CMD.value
        if sec_left <= 120:
            return DeviceCommand.PRE2_CMD.value
        if sec_left <= 300:
            return DeviceCommand.PRE5_CMD.value
        if sec_left <= 600:
            return DeviceCommand.PRE10_CMD.value
        return DeviceCommand.PRE_RACE_CMD.value

    # ------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------
    @Slot()
    def _on_debug_clicked(self):
        try:
            if not self.session_race_list:
                return

            rl = self.session_race_list  # RaceList

            dlg = DebugWindow(
                    self,
                    racelist=rl,
                    device_manager=self.device_man,
                    is_endurance=self.race_man.endurance,
                )
            dlg.show()  # VB: Show()

        except Exception as e:
            print(f"DEBUG CLICK ERROR: {e}")
    # ------------------------------------------------------------
    # Driver status apply
    # ------------------------------------------------------------
    @Slot()
    def _on_apply_status_clicked(self) -> None:
        if not (self.race_man and self.session_race_list):
            return
        row = self.refs.lap_table.currentRow()
        if row < 0:
            return
        idx = self.refs.status_box.currentIndex() + 5
        # mapping base (poi lo allineiamo perfetto al tuo RaceState)
        mapping = {
            0: RaceState.NOT_STARTED,
            1: RaceState.RACING,
            2: RaceState.FINISHED,
            3: RaceState.IN_PIT,
            4: RaceState.OUTLAP,
            5: RaceState.DNF,
            6: RaceState.DSQ,
            7: RaceState.DNS,
        }
        st = mapping.get(idx, RaceState.RACING)
        try:
            self.race_man.set_status(row, st)
        except Exception:
            pass
        self.write_lap_timing(self.session_race_list)
        log(f"[RaceWindow] Apply status: row={row} -> {st}")

    # ------------------------------------------------------------
    # Flags control (base)
    # ------------------------------------------------------------
    def _toggle_yellow(self, i: int) -> None:
        self.yellows[i] = not self.yellows[i]
        self.yellow_management()

    def yellow_management(self) -> None:
        if not self.device_man:
            return

        y1, y2, y3 = self.yellows
        if y1:
            if y2:
                if y3:
                    self.yellows = [False, False, False]
                    self._on_vsc_clicked()
                    return
                cmd = DeviceCommand.YELLOW_FS_CMD.value
            else:
                cmd = DeviceCommand.YELLOW_TF_CMD.value if y3 else DeviceCommand.YELLOW_F_CMD.value
        elif y2:
            cmd = DeviceCommand.YELLOW_ST_CMD.value if y3 else DeviceCommand.YELLOW_S_CMD.value
        elif y3:
            cmd = DeviceCommand.YELLOW_T_CMD.value
        else:
            cmd = DeviceCommand.CLC_YELLOW_CMD.value

        self.device_man.send_command(cmd, DeviceManager.DevicesIDs.Sem)
        log(f"[RaceWindow] YellowManagement -> {cmd}")

    def _on_green_clicked(self) -> None:
        if self.device_man:
            self.device_man.broadcast(DeviceCommand.GREEN_FLAG_CMD.value)
            log("FLAG Green")

    def _on_red_clicked(self) -> None:
        if self.device_man:
            self.device_man.broadcast(DeviceCommand.RED_FLAG_CMD.value)
            log("FLAG Red")

    def _on_clear_clicked(self) -> None:
        if self.device_man:
            self.device_man.send_command(DeviceCommand.CLC_CMD.value, DeviceManager.DevicesIDs.Sem)
            log("FLAG Clear")

    def _on_sc_clicked(self) -> None:
        if self.device_man:
            self.device_man.send_command(DeviceCommand.SAFETY_CAR_CMD.value, DeviceManager.DevicesIDs.Sem)
            log("FLAG SC")

    def _on_vsc_clicked(self) -> None:
        if self.device_man:
            self.device_man.send_command(DeviceCommand.FULL_YELLOW_CMD.value, DeviceManager.DevicesIDs.Sem)
            log("FLAG VSC")

    def _on_wet_clicked(self) -> None:
        if self.device_man:
            self.device_man.send_command(DeviceCommand.WET_RACE_CMD.value, DeviceManager.DevicesIDs.Sem)
            log("FLAG Wet")

    def _on_formation_lap_clicked(self) -> None:
        if self.device_man:
            self.device_man.send_command(DeviceCommand.FORMATION_LAP_CMD.value, DeviceManager.DevicesIDs.Sem)
            log("Formation lap")

    def _on_open_pit_clicked(self) -> None:
        if self.device_man:
            self.device_man.send_command(DeviceCommand.PIT_OPEN_CMD.value, DeviceManager.DevicesIDs.Sem)
            self.refs.pit_label.setText("Pit Open")
            log("Pit OPEN")

    def _on_close_pit_clicked(self) -> None:
        if self.device_man:
            self.device_man.send_command(DeviceCommand.PIT_CLOSER_CMD.value, DeviceManager.DevicesIDs.Sem)
            self.refs.pit_label.setText("Pit Closed")
            log("Pit CLOSED")

    def control_pit_lane_open(self) -> None:
        """
        Porting VB ControlPitLaneOpen()
        """
        if not self.device_man or not self.race_man:
            return

        try:
            # VB: DeviceMan.SendCommand(CLC_CMD, Sem)
            self.device_man.send_command(DeviceCommand.CLC_CMD, DeviceManager.DevicesIDs.Sem)

            # VB: Thread.Sleep(10)
            time.sleep(0.01)

            pit_state = self.race_man.pit_state

            if pit_state == 0:
                self.device_man.send_command(DeviceCommand.PIT_CLOSER_CMD, DeviceManager.DevicesIDs.Sem)

            elif pit_state == 1:
                self.device_man.send_command(DeviceCommand.PIT_OPEN_CMD, DeviceManager.DevicesIDs.Sem)

            elif pit_state == 2:
                self.device_man.send_command(DeviceCommand.PIT_VALID_CMD, DeviceManager.DevicesIDs.Sem)

        except Exception as e:
            log(f"[RaceWindow] control_pit_lane_open ERROR: {e}")

    # ------------------------------------------------------------
    # Transponder (placeholder; completamento endurance/swap nel prossimo step) -- NO
    # ------------------------------------------------------------
    
    def _index_for_number(self, lista: RaceList, number: int) -> int:
        try:
            n = int(number)
        except Exception:
            return -1
        try:
            for i, d in enumerate(lista.drivers):
                if int(getattr(d, "number", -1)) == n:
                    return i
        except Exception:
            pass
        return -1


    def _best_index(self, lista: RaceList, rm) -> int:
        try:
            best_num = getattr(rm, "best_lap_driver", None)
            if best_num is None:
                best_num = getattr(rm, "BestLapDriver", None)
            if best_num is None:
                return -1
            return self._index_for_number(lista, int(best_num))
        except Exception:
            return -1
    
    
    @Slot(int, int)
    def _on_transponder_gui_thread(self, device: int, number: int) -> None:
        if number == 0:
            return

        dm = self.device_man
        if dm is not None:
            flags = getattr(dm, "active_flags", None)
            if not flags or device < 0 or device >= len(flags) or not flags[device]:
                return

        rm = self.race_man
        rl = self.session_race_list
        if rm is None or rl is None:
            return

        t0 = perf_counter()
        swap = False

        # indice corrente (se esiste già)
        driver_index = self._index_for_number(rl, number)

        # --- endurance swap se non trovato
        if driver_index < 0:
            if not rm.endurance:
                return

            # trova roadster che contiene quel number
            roadster = None
            try:
                for r in rl.roadsters:
                    nums = getattr(r, "numbers", None) or []
                    if int(number) in [int(x) for x in nums]:
                        roadster = r
                        break
            except Exception:
                roadster = None

            if roadster is None:
                return

            # swap_index = indice del driver attuale di quel roadster
            try:
                actual_driver = roadster.getActualDriver
                swap_index = self._index_for_number(rl, int(actual_driver.number))
            except Exception:
                swap_index = -1

            if swap_index < 0:
                return

            # swap + update liste
            try:
                roadster.SwapDriver()
                rl.drivers[swap_index] = roadster.getActualDriver
                rl.reserve_drivers[swap_index] = roadster.getReserveDriver
            except Exception as e:
                log(f"[RaceWindow] swap ERROR: {e}")
                return

            # refresh mapping RaceManager
            self.session_race_list = rl
            try:
                rm.set_session_race_list(rl)
            except Exception:
                rm.session_race_list = rl

            # ora l'actual driver dovrebbe esistere in lista
            driver_index = self._index_for_number(rl, number)
            if driver_index < 0:
                return

            # start time reserve (se presente)
            try:
                rm.set_start_time_reserve(driver_index, device)
            except Exception:
                pass

            try:
                team = getattr(roadster, "team", None) or getattr(roadster, "Team", "")
                log(f"[RaceWindow] Driver Swap for {team}")
            except Exception:
                pass

            swap = True

        # --- lap done
        try:
            lap_state = rm.lap_done(driver_index, int(number), int(device), bool(swap))
            log(f"[RaceWindow] Pass: {lap_state}")
        except Exception as e:
            log(f"[RaceWindow] lap_done ERROR: {type(e).__name__}: {e}")
            log(traceback.format_exc())
            return

        # ✅ passed SOLO se non debounced/invalid
        # (meglio usare LapState enum: qui lascio una forma compatibile)
        
        
        # Dopo lap_done l'ordine può cambiare: ricalcola idx e best_idx sull'ordine ATTUALE
        idx = self._index_for_number(rl, number)
        best_idx = self._best_index(rl, rm)

        # --- UI refresh
        try:
            self._update_gui_after_pass(rl, idx=idx, best_idx=best_idx, swap=swap, lap_state=int(lap_state))
        except Exception as e:
            log(f"[RaceWindow] _update_gui_after_pass ERROR: {e}")

        dt_ms = int((perf_counter() - t0) * 1000)
        log(f"[RaceWindow] HandleTransponderPass took {dt_ms} ms (swap={swap}, idx={idx}, best_idx={best_idx})")


    # ------------------------------------------------------------
    # Save results (hook, poi integriamo ResultManager)
    # ------------------------------------------------------------
    def _on_save_results_clicked(self) -> None:
        log("Generate Result clicked (TODO: ResultManager)")

    # ------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------
    
    def _format_mmss(self, sec: int) -> str:
        if sec < 0:
            sec = 0
        m = sec // 60
        s = sec % 60
        return f"{m:02d}:{s:02d}"

    def _parse_active_flags(self, s: str) -> List[bool]:
        parts = [p.strip() for p in str(s).split(",") if p.strip()]
        flags = [p in ("1", "true", "True", "YES", "yes") for p in parts]
        while len(flags) < 6:
            flags.append(True)
        return flags[:6]

    def _get_local_ip_best_effort(self) -> str:
        """Ottiene l'IP locale della LAN usando get_local_ipv4() da net.py"""
        ip = get_local_ipv4()
        log(f"[LocalIP] Detected: {ip}")
        return ip if ip != "IP non trovato" else "0.0.0.0"

    def _shutdown_devices_async(self) -> None:
        """Helper run in background to broadcast DSCN and then disconnect.

        This keeps the UI thread responsive during window closing, avoiding
        hangs if sockets block.
        """
        if not self.device_man:
            return
        try:
            if self.device_man.conn_type == ConnectionTypes.TCP:
                try:
                    self.device_man.broadcast(DeviceCommand.DSCN_CMD.value)
                    log("DeviceManager: broadcast DSCN_CMD before shutdown (threaded)")
                except Exception as exc:
                    log(f"[RaceWindow] async broadcast DSCN_CMD error: {exc}")
        except Exception:
            # ignore if device_man mutated concurrently
            pass

        try:
            self.device_man.disconnect_all()
            log("DeviceManager disconnected (threaded)")
        except Exception as exc:
            log(f"[RaceWindow] async DeviceManager disconnect error: {exc}")

    def closeEvent(self, event) -> None:
        log("RaceManagerWindow closing...")

        self._ses_timer.stop()
        self._pos_timer.stop()
        self._pre_timer.stop()

        try:
            if self.live_man:
                self.live_man.stop()
                self.live_man = None
                log("LiveTiming stopped")
                log("LiveTiming stopped")
        except Exception as e:
            log(f"[RaceWindow] LiveTiming stop error: {e}")

        # perform device shutdown in a separate thread to prevent blocking
        if self.device_man:
            threading.Thread(target=self._shutdown_devices_async, daemon=True).start()

        super().closeEvent(event)
        
    def setup_laptimingtable(self) -> None:
        """
        VB: LapTimingViewSetup() -> PySide6
        """
        t = self.refs.lap_table  # QTableWidget

        # --- equivalente Anchor = Left|Right|Top|Bottom ---
        # In Qt non si usa Anchor: lo fa il layout (SizePolicy + layout stretch).
        # (già ok se la tabella è in un layout con stretch)

        # --- colonne (width VB) ---
        self._vb_col_widths = [50, 200, 200, 100, 100, 100, 125, 50, 100, 100, 100, 150, 125]

        # --- NotSortable ---
        t.setSortingEnabled(False)
        h = t.horizontalHeader()
        h.setSectionsClickable(False)     # blocca anche l'intento di sort via click
        h.setSectionsMovable(False)

        # --- row headers ---
        t.verticalHeader().setVisible(False)

        # --- selection style / behavior ---
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # --- alignment header ---
        h.setDefaultAlignment(Qt.AlignCenter)

        # --- applichiamo width VB ---
        # Opzione A (default): width fisse VB + scroll se finestra troppo stretta
        for i, w in enumerate(self._vb_col_widths):
            h.setSectionResizeMode(i, QHeaderView.Fixed)
            t.setColumnWidth(i, w)

        # --- alignment celle: centro di default, Pilota/Team a sinistra ---
        # Nota: l'allineamento delle celle in QTableWidget si imposta item-per-item.
        # Quindi lo applichi mentre scrivi la riga (vedi helper sotto).
    
    def _set_table_row(self, row: int, values: list[str]) -> None:
        t = self.refs.lap_table
        if row >= t.rowCount():
            t.setRowCount(row + 1)

        for col, val in enumerate(values):
            item = QTableWidgetItem("" if val is None else str(val))

            # Default center
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignHCenter)

            # Colonna 1 (Pilota) e 2 (Team) left
            if col in (1, 2):
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            t.setItem(row, col, item)