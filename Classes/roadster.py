from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import List

from Classes.driver import Driver


@dataclass
class Roadster:
    """
    Runtime endurance "roadster" (team with 2 drivers).

    Compatibility targets:
    - RaceList.__post_init__ expects:
        - .numbers (List[int])
        - .team (str)
        - .get_actual_driver()
        - .get_reserve_driver()
    - Your VB-ported handler may call:
        - .SwapDriver()
        - .getActualDriver / .getReserveDriver (VB-like)
    """

    first_driver: Driver
    second_driver: Driver

    # 1 = first, 2 = second
    actual_driver: int = 1

    race_time: timedelta = field(default_factory=lambda: timedelta(0))

    # runtime-computed
    numbers: List[int] = field(default_factory=list)
    team: str = ""

    def __post_init__(self) -> None:
        # Ensure ints
        self.numbers = [int(self.first_driver.number), int(self.second_driver.number)]

        # Prefer explicit team on driver if present; fallback to first driver team
        self.team = getattr(self.first_driver, "team", "") or ""

        # Start with first driver active by default
        self.actual_driver = 1

    # ----------------------------
    # Driver selection (core API)
    # ----------------------------
    def get_actual_driver(self) -> Driver:
        return self.first_driver if self.actual_driver == 1 else self.second_driver

    def get_reserve_driver(self) -> Driver:
        return self.second_driver if self.actual_driver == 1 else self.first_driver

    # ----------------------------
    # VB-like aliases (for your handler)
    # ----------------------------
    @property
    def getActualDriver(self) -> Driver:
        return self.get_actual_driver()

    @property
    def getReserveDriver(self) -> Driver:
        return self.get_reserve_driver()

    def SwapDriver(self) -> None:
        """VB-like alias."""
        self.swap_driver()

    # ----------------------------
    # Core behavior
    # ----------------------------
    def swap_driver(self) -> None:
        """
        Swap endurance driver WITHOUT duplicating lap_history.
        Transfers 'race state' from active driver to the one entering.
        """
        if self.actual_driver == 1:
            src = self.first_driver
            dst = self.second_driver
            self.actual_driver = 2
            # reset sector progression of the driver leaving (VB behavior)
            self.first_driver.actual_sector = 1
        else:
            src = self.second_driver
            dst = self.first_driver
            self.actual_driver = 1
            self.second_driver.actual_sector = 1

        # --- copy base race state ---
        dst.time_on_track = src.time_on_track
        dst.laps = src.laps
        dst.race_status = src.race_status

        # carry endurance timing context
        dst.set_endurance_start_time(
            time_value=src.race_time,
            start_time=src.start_time,
            sort_time=src.sort_time,
        )

        # --- handover: do NOT extend, do NOT duplicate ---
        dst.sectors = list(src.sectors)
        dst.lap_history = list(src.lap_history)

    def add_race_time(self) -> None:
        """Accumulate time_on_track of the currently active driver."""
        self.race_time += self.get_actual_driver().time_on_track

    def start_time_all(self) -> None:
        """Set start time for both drivers."""
        self.first_driver.set_start_time()
        self.second_driver.set_start_time()

    # ----------------------------
    # Export / views
    # ----------------------------
    def to_race_list(self) -> str:
        return f"EQUIP - {self.team} - {self.first_driver.surname}/{self.second_driver.surname}"

    def to_file(self) -> str:
        return f"{self.team}|{self.first_driver.driver_id}|{self.second_driver.driver_id}\r\n"

    def to_lap_timing(self):
        return self.get_actual_driver().to_lap_timing()

    def to_live(self) -> str:
        return self.get_actual_driver().to_live()

    def to_result(self) -> str:
        return f"{self.first_driver.surname} / {self.second_driver.surname}"
    
