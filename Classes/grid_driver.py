from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GridDriver:
    name: str
    surname: str
    race_number: int
    team: str
    position: int
    best_lap: str

    # Penalità
    grid_drop: int = 0
    desired_pos_after_penalty: int = 0
    pit_lane_start: bool = False

    def name_surname(self) -> str:
        initials = " ".join([f"{p[0]}." for p in self.name.split() if p])
        return f"{initials} {self.surname}  | #{self.race_number}"
