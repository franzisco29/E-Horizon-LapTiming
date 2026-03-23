from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from Modules.enums import RaceState
from Modules.time_format import fmt_mm_ss_mmm, fmt_ss_mmm


@dataclass
class Driver:
    # --- campi base ---
    driver_id: int
    name: str
    surname: str
    number: int              # in VB: DIVENTA TRANSP ID
    team: str
    pro: bool
    race_number: int         # VB: rnumber_

    # --- stato gara ---
    race_status: RaceState = RaceState.NOT_STARTED
    laps: int = 0
    position: int = 0
    
    isFastestDriver: bool = False # flag per evidenziare il miglior tempo in classifica (VB: BestLapDrv)

    delta: timedelta = field(default_factory=lambda: timedelta(0))
    leader_delta: timedelta = field(default_factory=lambda: timedelta(0))

    fast_lap: timedelta = field(default_factory=lambda: timedelta(0))
    last_lap: timedelta = field(default_factory=lambda: timedelta(0))

    lap_history: List[timedelta] = field(default_factory=list)
    position_history: List[int] = field(default_factory=list)

    # (leader, previous)
    laps_behind: List[int] = field(default_factory=lambda: [0, 0])

    time_on_track: timedelta = field(default_factory=lambda: timedelta(0))

    # settori (3)
    sectors: List[timedelta] = field(default_factory=lambda: [timedelta(0), timedelta(0), timedelta(0)])
    sector_race_time: List[datetime] = field(default_factory=lambda: [datetime.min, datetime.min, datetime.min])
    actual_sector: int = 1

    # tempi usati per lap/ordinamenti
    race_time: datetime = field(default_factory=datetime.now)     # VB: ONLY FOR LAP TIMES
    sort_time: datetime = field(default_factory=datetime.now)
    start_time: datetime = field(default_factory=datetime.now)

    # pit
    pit_in_times: List[timedelta] = field(default_factory=list)   # offset da start_time
    pit_times: List[timedelta] = field(default_factory=list)
    pit_enter_time: Optional[datetime] = None

    def __post_init__(self) -> None:
        self.reset_sectors()
        self.laps = 0
        if self.laps_behind is None or len(self.laps_behind) != 2:
            self.laps_behind = [0, 0]

    # -------------------
    # Core timing methods
    # -------------------
    def reset_sectors(self) -> None:
        self.sectors = [timedelta(0), timedelta(0), timedelta(0)]

    def _find_best_lap(self, race: bool) -> None:
        """
        VB: Find_best_lap(race)
        Se race=True, salta il primo giro (outlap). Se non ci sono >=2 giri, esce.
        """
        if not self.lap_history:
            return

        if race:
            start_index = 1
            if self.laps < 2 or len(self.lap_history) < 2:
                return
        else:
            start_index = 0

        best = self.lap_history[start_index]
        for t in self.lap_history[start_index:]:
            if t < best:
                best = t
        self.fast_lap = best

    def get_lap(self, sect: bool, race: bool) -> None:
        """
        VB: GetLap(sect, race)
        """
        new_time = datetime.now()
        lap_time = new_time - self.race_time

        self.laps += 1
        self.lap_history.append(lap_time)
        self.last_lap = lap_time

        self._find_best_lap(race)

        self.race_time = new_time
        self.sort_time = new_time

        if sect:
            self.get_sector(3)

    def get_sector(self, sect: int) -> None:
        """
        VB: GetSector(sect)
        sect: 1..3
        """
        new_time = datetime.now()

        if sect == 1:
            self.reset_sectors()
            sec_time = new_time - self.race_time
        else:
            # VB: sector_race_time(sect - 2)
            prev_idx = sect - 2
            prev_time = self.sector_race_time[prev_idx]
            sec_time = new_time - prev_time

        self.sort_time = new_time
        self.sectors[sect - 1] = sec_time
        self.sector_race_time[sect - 1] = new_time

        if sect == 3:
            self.actual_sector = 1
        else:
            self.actual_sector += 1

    # -------------------
    # Utility / status
    # -------------------
    def save_position(self) -> None:
        self.position_history.append(self.position)

    def in_pit(self, race: bool) -> None:
        new_time = datetime.now()
        self.sort_time = new_time

        if race:
            self.pit_enter_time = new_time
            self.pit_in_times.append(new_time - self.start_time)

    def out_lap(self, sect: bool, race: bool) -> None:
        new_time = datetime.now()
        self.sort_time = new_time
        self.race_time = new_time
        if race:
            if self.pit_enter_time is None:
                self.pit_times.append(timedelta(0))
            else:
                self.pit_times.append(new_time - self.pit_enter_time)

    def finish(self) -> None:
        self.race_status = RaceState.FINISHED

    def set_start_time(self) -> None:
        now = datetime.now()
        self.race_time = now
        self.sort_time = now
        self.start_time = now

    def set_endurance_start_time(self, time_value: datetime, start_time: datetime, sort_time: datetime) -> None:
        self.race_time = time_value
        self.sort_time = sort_time
        self.start_time = start_time

    # -------------------
    # Formatting / export
    # -------------------
    def to_file(self) -> str:
        # VB: Id|Name|Surname|Team|Number|Pro|Race_Number + CRLF
        return f"{self.driver_id}|{self.name}|{self.surname}|{self.team}|{self.number}|{self.pro}|{self.race_number}\r\n"

    def to_race_list(self) -> str:
        return f"{self.driver_id} - {self.name} {self.surname} - {self.team}"

    def name_surname(self) -> str:
        initials = " ".join([f"{p[0]}." for p in self.name.split() if p])
        return f"#{self.race_number:02d} | {initials} {self.surname}"

    def fst_lap_to_res(self, endurance: bool) -> str:
        if endurance:
            return f"{self.team}: {fmt_mm_ss_mmm(self.fast_lap)}"
        return f"{self.name_surname()}: {fmt_mm_ss_mmm(self.fast_lap)}"

    def _sector_to_string(self, idx: int) -> str:
        t = self.sectors[idx]
        if t.total_seconds() <= 0:
            return " "
        return fmt_ss_mmm(t)

    def get_status_string(self) -> str:
        mapping = {
            RaceState.NOT_STARTED: "Not Started",
            RaceState.RACING: "Racing",
            RaceState.FINISHED: "Finished",
            RaceState.IN_PIT: "In Pit",
            RaceState.OUTLAP: "OutLap",
            RaceState.DNF: "DNF",
            RaceState.DSQ: "DSQ",
            RaceState.DNS: "DNS",
        }
        return mapping.get(self.race_status, "Error")

    def print_delta(self, interval: bool) -> str:
        if self.position == 1:
            return "Interval" if interval else "Leader"

        if interval:
            if self.laps_behind[1] > 1:
                return f"+{self.laps_behind[1] - 1}L"
            return f"+{fmt_ss_mmm(self.delta)}"
        else:
            if self.laps_behind[0] > 1:
                return f"+{self.laps_behind[0] - 1}L"
            return f"+{fmt_ss_mmm(self.leader_delta)}"

    def to_lap_timing(self) -> List[str]:
        status = self.get_status_string()
        name = self.name_surname()

        # VB: TimeOnTrack = Sort_Time - start_time_
        self.time_on_track = self.sort_time - self.start_time

        interval = self.print_delta(True)
        gap = self.print_delta(False)

        return [
            str(self.position),
            name,
            self.team,
            self._sector_to_string(0),
            self._sector_to_string(1),
            self._sector_to_string(2),
            fmt_mm_ss_mmm(self.last_lap),
            str(self.laps),
            status,
            gap,
            interval,
            fmt_mm_ss_mmm(self.fast_lap),
            fmt_mm_ss_mmm(self.time_on_track),
        ]

    def to_live_dict(self) -> dict:
        """Dict ready for LiveTiming (stable IDs + same columns as UI)."""
        status = self.get_status_string()
        name = self.name_surname()

        # NOTE: keep same formatting as UI table
        self.time_on_track = self.race_time - self.start_time
        interval = self.print_delta(True)
        gap = self.print_delta(False)

        return {
            # stable identifiers
            "driverId": int(self.driver_id),
            "transponderNumber": int(self.number),
            "number": int(self.race_number),

            # table fields
            "position": int(self.position),
            "name_surname": name,
            "name": self.name,
            "surname": self.surname,
            "team": self.team,
            "sector1": self._sector_to_string(0),
            "sector2": self._sector_to_string(1),
            "sector3": self._sector_to_string(2),
            "lastLap": fmt_mm_ss_mmm(self.last_lap),
            "laps": int(self.laps),
            "status": status,
            "gap": gap,
            "interval": interval,
            "fastLap": fmt_mm_ss_mmm(self.fast_lap),
            "timeOnTrack": fmt_mm_ss_mmm(self.time_on_track),
            "isBestLap": self.isFastestDriver,
            
        }

    def to_live(self) -> str:
        """
        VB: crea oggetto anonimo e serializza JSON.
        In Python facciamo dict + json.dumps.
        """
        import json

        driver_data = self.to_live_dict()

        return json.dumps(driver_data, ensure_ascii=False, separators=(",", ":"))

    def order_pit_times(self) -> None:
        if self.pit_times:
            self.pit_times.sort()
        else:
            self.pit_times.append(timedelta.max)
            self.pit_times.sort()