from __future__ import annotations
from enum import IntEnum

class RaceState(IntEnum):
    NOT_STARTED = 0
    RACING = 1
    FINISHED = 2
    IN_PIT = 3
    OUTLAP = 4
    DNF = 5
    DSQ = 6
    DNS = 7
