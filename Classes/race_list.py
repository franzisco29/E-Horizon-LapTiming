from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from Classes.driver import Driver

# Import opzionale: se non hai ancora Roadster, lascia come stringa (forward ref)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Classes.roadster import Roadster


@dataclass
class RaceList:
    """
    RaceList (Python) - equivalente VB.

    - Può essere una lista "normale" (drivers)
    - oppure una lista endurance (roadsters) dove:
        drivers = [r.get_actual_driver() ...]
        reserve_drivers = [r.get_reserve_driver() ...]
    """

    name: str
    drivers: List[Driver] = field(default_factory=list)
    reserve_drivers: List[Driver] = field(default_factory=list)
    roadsters: Optional[List["Roadster"]] = None
    endurance_list: bool = False

    def __post_init__(self) -> None:
        # Se roadsters è valorizzato, costruiamo drivers + reserve_drivers da lì
        if self.roadsters is not None:
            self.endurance_list = True
            self.drivers = [r.get_actual_driver() for r in self.roadsters]
            self.reserve_drivers = [r.get_reserve_driver() for r in self.roadsters]
        else:
            self.endurance_list = False
            # drivers già passato dall’esterno; reserve_drivers può rimanere vuoto

    # --------------------
    # VB: toFile()
    # --------------------
    def to_file(self) -> str:
        if self.endurance_list and self.roadsters is not None:
            return "".join(r.to_file() for r in self.roadsters)
        return "".join(d.to_file() for d in self.drivers)

    # --------------------
    # VB: getFileName()
    # In Python: l'estensione la prendiamo da config/ruleset, non da My.Resources
    # --------------------
    def get_file_name(self, endurance_ext: str = ".endracelist", normal_ext: str = ".racelist") -> str:
        ext = endurance_ext if self.endurance_list else normal_ext
        return f"{self.name}_RaceList{ext}"
