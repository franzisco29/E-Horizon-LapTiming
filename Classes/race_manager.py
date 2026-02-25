from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Dict, List, Optional

from Classes.session import Session, SessionTypes, SessionState
from Classes.race_list import RaceList
from Classes.driver import Driver

from Modules.enums import RaceState


# Se hai già DevicesIDs altrove, importalo e rimuovi questo.
class DevicesIDs(IntEnum):
    Central = 0
    S1 = 1
    S2 = 2
    PitIn = 3
    PitOut = 4
    Sem = 5


class LapState(IntEnum):
    Invalid = -1
    Valid = 1
    OutLap = 2
    InPit = 3


@dataclass
class RaceManager:
    """
    RaceManager - versione Python (fase 1) compatibile col tuo Driver.
    Gestisce:
    - start/stop/end session
    - lap/sector/pit events
    - ordering + delta + best lap
    - JSON live della sessione (delegato a Session)
    """

    _session_type: int
    debounce_ms: int

    session_race_list: Optional[RaceList] = None

    session: Session = field(init=False)
    best_lap_driver: int = 0  # transponder ID (Driver.number)

    # Debounce tracking per transponder ID (Driver.number)
    last_device_detected: Dict[int, int] = field(default_factory=dict)     # number -> device id
    last_time_detected: Dict[int, datetime] = field(default_factory=dict)  # number -> last timestamp

    # lookup veloce number -> Driver
    driver_by_number: Dict[int, Driver] = field(default_factory=dict)

    # --- Time-certain finish (time based races) ---
    # Latch che diventa True quando il tempo arriva a 0 (gestito nel setter di session_time)
    time_over: bool = False
    # True quando il leader completa il giro dopo time_over/session finished
    leader_finished: bool = False
    # (debug) giro a cui il leader ha chiuso
    leader_finish_lap: Optional[int] = None

    def __post_init__(self) -> None:
        self.session = Session(self._session_type)

        if self.session_race_list is not None:
            self.set_session_race_list(self.session_race_list)

    # ============================================================
    # Setup
    # ============================================================

    def set_session_race_list(self, value: RaceList) -> None:
        """
        Imposta la race list corrente e ricostruisce la mappa number -> Driver.
        Va chiamato SEMPRE quando cambi lista (load incluso), per evitare mismatch/KeyError.
        """
        self.session_race_list = value
        drivers = value.drivers if value and getattr(value, "drivers", None) else []
        self.driver_by_number = {d.number: d for d in drivers}

        # reset flags/time-over (nuova sessione/lista)
        self.time_over = False
        self.leader_finished = False
        self.leader_finish_lap = None

    # ============================================================
    # Shortcuts
    # ============================================================

    @property
    def session_type(self) -> int:
        return int(self.session.session_type)


    @session_type.setter
    def session_type(self, value: int) -> None:
        value = int(value)
        self._session_type = value
        # aggiorna tipo
        self.session.session_type = value

        # 🔁 aggiorna status automaticamente
        self.session.session_status = (
            int(SessionState.Starting)
            if self.session.is_race()
            else int(SessionState.NotStarted)
        )

        # 🔁 resetta anche il timer coerentemente
        try:
            self.session.session_time = self.session.max_session_time[value]
        except Exception:
            pass

    @property
    def race(self) -> bool:
        return self.session.is_race()

    @property
    def endurance(self) -> bool:
        return self.session.is_endurance()

    @property
    def session_time(self) -> int:
        return self.session.session_time

    @session_time.setter
    def session_time(self, value: int) -> None:
        # Clamp + latch: quando arrivi a 0, time_over resta True (evita edge-case con valori negativi)
        v = int(value)
        if v <= 0:
            self.session.session_time = 0
            if not self.time_over:
                self.time_over = True
        else:
            self.session.session_time = v

    @property
    def session_status(self) -> int:
        return self.session.session_status

    @session_status.setter
    def session_status(self, value: int) -> None:
        self.session.session_status = int(value)
        
    @property
    def pit_state(self) -> int:
        return int(self.session.pit_state)
    
    def open_pit(self) -> bool:
        return self.session.open_pit()
    

    # ============================================================
    # Session control
    # ============================================================

    def start_session(self) -> None:
        """
        VB StartSession:
        - SessionStatus = Started
        - PitState = 1
        - per ogni driver: set_start_time + init debounce maps
        - set stato iniziale driver
        """
        if not self.session_race_list:
            return

        self.session_status = int(SessionState.Started)
        self.session.pit_state = 1

        # reset finish flags
        self.time_over = False
        self.leader_finished = False
        self.leader_finish_lap = None

        now = datetime.now()
        for d in self.session_race_list.drivers:
            d.set_start_time()
            self.last_device_detected[d.number] = int(DevicesIDs.Central)
            self.last_time_detected[d.number] = now

        self._set_all_start_status()

    def end_session(self) -> None:
        """
        VB EndSession:
        - SessionStatus = Finished
        - se NON race: se driver in pit => finish
        - PitState = 0
        """
        if not self.session_race_list:
            return

        self.session_status = int(SessionState.Finished)
        # consideriamo la sessione chiusa come "time over" per la logica di chiusura giro
        self.time_over = True

        if not self.race:
            for d in self.session_race_list.drivers:
                if d.race_status == RaceState.IN_PIT:
                    d.finish()

        self.session.pit_state = 0

    def stop_session(self) -> None:
        self.session_status = int(SessionState.Stopped)
        self.session.pit_state = 0

    def resume_session(self) -> None:
        self.session_status = int(SessionState.Started)
        self.session.pit_state = 1

        # reset finish flags
        self.time_over = False
        self.leader_finished = False
        self.leader_finish_lap = None

    def reset_session(self) -> None:
        self.session_status = int(SessionState.NotStarted)
        self.time_over = False
        self.leader_finished = False
        self.leader_finish_lap = None

        # reset debounce maps (coerente con VB)
        self.last_device_detected.clear()
        self.last_time_detected.clear()

    # ============================================================
    # Live / naming / points
    # ============================================================

    def session_to_live(self) -> str:
        return self.session.to_live_json(index=-1)

    def get_session_name(self) -> str:
        return self.session.get_session_name()

    def get_points(self, pos: int, best: bool):
        return self.session.get_points(pos, best)

    # ============================================================
    # Reserve start time helper (VB SetStartTimeReserve)
    # ============================================================

    def set_start_time_reserve(self, in_driver_index: int, device: int) -> None:
        if not self.session_race_list:
            return
        d = self.session_race_list.drivers[in_driver_index]
        self.last_device_detected[d.number] = int(device)
        self.last_time_detected[d.number] = datetime.now()

    # ============================================================
    # Helpers (safe lookup / resolve index)
    # ============================================================

    def _get_driver_safe(self, number: int) -> Optional[Driver]:
        """Recupera un Driver senza mai sollevare KeyError."""
        drv = self.driver_by_number.get(int(number))
        if drv is not None:
            return drv
        if self.session_race_list and self.session_race_list.drivers:
            return next((d for d in self.session_race_list.drivers if d.number == int(number)), None)
        return None

    def _resolve_driver_index(self, fallback_index: int, number: int) -> int:
        """
        Allinea driver_index (UI) e number (transponder). Se mismatch, trova l'indice corretto per number.
        """
        if not self.session_race_list or not self.session_race_list.drivers:
            return fallback_index

        drivers = self.session_race_list.drivers
        if 0 <= fallback_index < len(drivers) and drivers[fallback_index].number == int(number):
            return fallback_index

        for i, d in enumerate(drivers):
            if d.number == int(number):
                return i

        return fallback_index

    def _mark_driver_finished(self, number: int, reason: str = "") -> bool:
        drv = self._get_driver_safe(int(number))
        if drv is None:
            return False
        if drv.race_status == RaceState.FINISHED:
            return False
        drv.race_status = RaceState.FINISHED
        return True

    def _apply_finish_on_central(self, number: int) -> None:
        """
        Applica la logica di fine gara SOLO al completamento giro (Central):
        - quando il tempo è finito (time_over=True) *oppure* session_status=Finished
        - il leader chiude per primo; dopo che il leader ha chiuso, tutti chiudono al loro primo Central.
        Copre anche il caso in cui un altro diventa leader dopo lo 0.
        """
        if not self.race:
            # Per practice/quali: se la sessione è finita, chiude al prossimo passaggio Central
            if self.session_status == int(SessionState.Finished):
                self._mark_driver_finished(number, reason="NON_RACE_FINISHED")
            return

        if not self.session_race_list or not self.session_race_list.drivers:
            return

        # condizione di attivazione: tempo finito o sessione marcata Finished
        if not (self.time_over or self.session_status == int(SessionState.Finished)):
            return

        leader_number = self.session_race_list.drivers[0].number

        if not self.leader_finished:
            # chiude il leader "attuale" (post-sorting)
            if int(number) == int(leader_number):
                if self._mark_driver_finished(number, reason="LEADER_CLOSES"):
                    self.leader_finished = True
                    drv = self._get_driver_safe(number)
                    self.leader_finish_lap = getattr(drv, "laps", None) if drv else None
            return

        # leader già chiuso -> chiude chiunque al prossimo Central
        self._mark_driver_finished(number, reason="AFTER_LEADER")
    # ============================================================
    # Main event: lap_done
    # ============================================================

    def lap_done(self, driver_index: int, number: int, device: int, swap: bool) -> int:
        """
        VB lapDone(id, number, device, swap)
        - driver_index: indice in lista (come VB)
        - number: transponder id (Driver.number)
        - device: DevicesIDs (0..)
        - swap: endurance swap logic (debounce bypass)
        """
        if not self.session_race_list or device < 0:
            return int(LapState.Invalid)

        driver_index = self._resolve_driver_index(driver_index, number)
        driver = self.session_race_list.drivers[driver_index]

        lap_state = self._set_lap_status(
            driver_index=driver_index,
            device=int(device),
            actual_status=driver.race_status,
            swap=bool(swap),
            number=int(number),
        )

        # --- Azioni per device solo se stato lo consente ---
        if lap_state == LapState.Valid:
            if device == int(DevicesIDs.Central):
                driver.get_lap(self.session.sectors_on, self.race)
                self.best_lap_driver = self._best_lap_find(self.session_race_list.drivers)
                self._calculate_delta()

            elif device == int(DevicesIDs.S1):
                driver.get_sector(1)
                self._calculate_delta()

            elif device == int(DevicesIDs.S2):
                driver.get_sector(2)
                self._calculate_delta()

            elif device == int(DevicesIDs.PitIn):
                driver.in_pit(self.race)
                self._calculate_delta()

            elif device == int(DevicesIDs.PitOut):
                driver.out_lap(self.session.sectors_on, self.race)
                self._calculate_delta()

            # Applica logica di fine gara (time-certain / session-finished) dopo sorting/delta
            self._apply_finish_on_central(number)

            return int(lap_state)

        if lap_state == LapState.OutLap:
            driver.out_lap(self.session.sectors_on, self.race)
            self._calculate_delta()
            return int(lap_state)

        if lap_state == LapState.InPit:
            driver.in_pit(self.race)
            self._calculate_delta()
            return int(lap_state)

        return int(LapState.Invalid)

    # ============================================================
    # Ordering + delta
    # ============================================================

    def _calculate_delta(self) -> None:
        if not self.session_race_list or not self.session_race_list.drivers:
            return

        self._order_race_list(self.race)

        drivers = self.session_race_list.drivers
        leader = drivers[0]

        for i in range(1, len(drivers)):
            cur = drivers[i]
            prev = drivers[i - 1]

            if self.race:
                cur.delta = cur.sort_time - prev.sort_time
                cur.leader_delta = cur.sort_time - leader.sort_time

                # laps behind (previous and leader)
                cur.laps_behind[1] = max(0, prev.laps - cur.laps)
                cur.laps_behind[0] = max(0, leader.laps - cur.laps)
            else:
                cur.delta = cur.fast_lap - prev.fast_lap
                cur.leader_delta = cur.fast_lap - leader.fast_lap

    def _order_race_list(self, race: bool) -> None:
        if not self.session_race_list:
            return

        drivers = self.session_race_list.drivers

        if race:
            # VB: laps desc, se sectors_on: actual_sector desc, poi sort_time asc
            def key(d: Driver):
                sec_rank = -d.actual_sector if self.session.sectors_on else 0
                return (-d.laps, sec_rank, d.sort_time)

            drivers.sort(key=key)
        else:
            # VB: fast_lap==0 va in fondo, altrimenti ascending
            def key(d: Driver):
                if d.fast_lap.total_seconds() <= 0:
                    return (1, timedelta.max)
                return (0, d.fast_lap)

            drivers.sort(key=key)

        for idx, d in enumerate(drivers):
            d.position = idx + 1

    # ============================================================
    # Status helpers
    # ============================================================

    def _set_all_start_status(self) -> None:
        if not self.session_race_list:
            return

        status = RaceState.RACING if self.race else RaceState.IN_PIT
        for d in self.session_race_list.drivers:
            d.race_status = status

    def set_status(self, driver_index: int, status: RaceState) -> None:
        if not self.session_race_list:
            return
        self.session_race_list.drivers[driver_index].race_status = status

    def all_ended(self) -> bool:
        if not self.session_race_list:
            return True

        for d in self.session_race_list.drivers:
            if d.race_status != RaceState.FINISHED:
                # VB: se < DNF e != Finished => false
                if int(d.race_status) < int(RaceState.DNF):
                    return False
                if d.race_status != RaceState.FINISHED:
                    return False
        return True

    # ============================================================
    # Best lap
    # ============================================================

    def _best_lap_find(self, drivers: List[Driver]) -> int:
        valid = [d for d in drivers if d.fast_lap.total_seconds() > 0]
        if not valid:
            return 0
        best = min(valid, key=lambda d: d.fast_lap)
        return int(best.number)

    # ============================================================
    # Debounce + state machine (VB setLapStatus)
    # ============================================================

    def _is_debounced(self, transponder_number: int, swap: bool) -> bool:
        if swap:
            return False
        last = self.last_time_detected.get(transponder_number)
        if last is None:
            return False
        return (datetime.now() - last) < timedelta(milliseconds=int(self.debounce_ms))

    def _set_lap_status(
        self,
        driver_index: int,
        device: int,
        actual_status: RaceState,
        swap: bool,
        number: int,
    ) -> LapState:
        """
        Replica della logica VB setLapStatus:
        - debounce sul transponder (Driver.number)
        - accetta se cambia device o device==Central o swap
        - ritorna LapState.Valid / OutLap / Invalid
        """
        if not self.session_race_list:
            return LapState.Invalid

        driver_index = self._resolve_driver_index(driver_index, number)
        driver = self.session_race_list.drivers[driver_index]

        if self._is_debounced(driver.number, swap):
            return LapState.Invalid

        last_dev = self.last_device_detected.get(driver.number)

        if not (last_dev != device or device == int(DevicesIDs.Central) or swap):
            return LapState.Invalid

        self.last_device_detected[driver.number] = device

        # ========== CENTRAL ==========
        if device == int(DevicesIDs.Central):
            if actual_status == RaceState.NOT_STARTED:
                driver.race_status = RaceState.RACING
                return LapState.Invalid

            if actual_status == RaceState.RACING:
                driver.race_status = RaceState.RACING

                if self.session_status == int(SessionState.Finished):
                    if self.race:
                        # In race: la chiusura effettiva è gestita in lap_done dopo ordering.
                        # Qui non forziamo FINISHED per evitare mismatch di indice.
                        pass
                    else:
                        driver.race_status = RaceState.FINISHED

                self.last_time_detected[driver.number] = datetime.now()
                return LapState.Valid

            if actual_status == RaceState.FINISHED:
                driver.race_status = RaceState.FINISHED
                return LapState.Invalid

            if actual_status == RaceState.IN_PIT:
                driver.race_status = RaceState.RACING
                self.last_time_detected[driver.number] = datetime.now()
                return LapState.Valid if self.race else LapState.OutLap

            if actual_status == RaceState.OUTLAP:
                driver.race_status = RaceState.RACING
                self.last_time_detected[driver.number] = datetime.now()

                if self.session_status == int(SessionState.Finished):
                    if self.race:
                        # In race: la chiusura effettiva è gestita in lap_done dopo ordering.
                        # Qui non forziamo FINISHED per evitare mismatch di indice.
                        pass
                    else:
                        driver.race_status = RaceState.FINISHED

                return LapState.Valid if self.race else LapState.OutLap

            return LapState.Invalid

        # ========== SECTORS (S1/S2) ==========
        if device in (int(DevicesIDs.S1), int(DevicesIDs.S2)):
            if actual_status == RaceState.NOT_STARTED:
                driver.race_status = RaceState.RACING
                return LapState.Invalid

            if actual_status == RaceState.RACING:
                driver.race_status = RaceState.RACING
                self.last_time_detected[driver.number] = datetime.now()
                return LapState.Valid

            if actual_status == RaceState.FINISHED:
                driver.race_status = RaceState.FINISHED
                return LapState.Invalid

            if actual_status == RaceState.IN_PIT:
                driver.race_status = RaceState.RACING
                self.last_time_detected[driver.number] = datetime.now()
                return LapState.Valid if self.race else LapState.OutLap

            if actual_status == RaceState.OUTLAP:
                self.last_time_detected[driver.number] = datetime.now()
                if self.race:
                    driver.race_status = RaceState.RACING
                    return LapState.Valid
                return LapState.OutLap

            return LapState.Invalid

        # ========== PIT IN ==========
        if device == int(DevicesIDs.PitIn):
            if actual_status == RaceState.NOT_STARTED:
                driver.race_status = RaceState.IN_PIT
                return LapState.Invalid

            if actual_status == RaceState.RACING:
                driver.race_status = RaceState.IN_PIT
                self.last_time_detected[driver.number] = datetime.now()
                return LapState.Valid

            if actual_status == RaceState.FINISHED:
                driver.race_status = RaceState.FINISHED
                return LapState.Invalid

            if actual_status == RaceState.IN_PIT:
                driver.race_status = RaceState.IN_PIT
                self.last_time_detected[driver.number] = datetime.now()
                return LapState.Invalid

            if actual_status == RaceState.OUTLAP:
                driver.race_status = RaceState.IN_PIT
                self.last_time_detected[driver.number] = datetime.now()
                return LapState.Invalid

            return LapState.Invalid

        # ========== PIT OUT ==========
        if device == int(DevicesIDs.PitOut):
            if actual_status == RaceState.NOT_STARTED:
                driver.race_status = RaceState.OUTLAP
                return LapState.Invalid

            if actual_status == RaceState.RACING:
                driver.race_status = RaceState.OUTLAP
                self.last_time_detected[driver.number] = datetime.now()
                return LapState.Valid

            if actual_status == RaceState.FINISHED:
                driver.race_status = RaceState.FINISHED
                return LapState.Invalid

            if actual_status == RaceState.IN_PIT:
                driver.race_status = RaceState.OUTLAP
                self.last_time_detected[driver.number] = datetime.now()
                return LapState.OutLap if (self.endurance or self.race) else LapState.Invalid

            if actual_status == RaceState.OUTLAP:
                driver.race_status = RaceState.OUTLAP
                self.last_time_detected[driver.number] = datetime.now()
                return LapState.Invalid

            return LapState.Invalid

        return LapState.Invalid

    # ============================================================
    # Extra
    # ============================================================

    def save_position(self) -> None:
        if not self.session_race_list:
            return
        for d in self.session_race_list.drivers:
            d.save_position()
