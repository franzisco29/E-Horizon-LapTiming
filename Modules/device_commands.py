from __future__ import annotations

from enum import Enum


class DeviceCommand(str, Enum):
    # CMD OF CONNECTION & UTILITIES
    CONN = "C"
    DSCN = "c"
    FAN = "W"

    # CMD FOR START
    START_PROC = "s"
    START = "S"

    # CMD FOR FLAGS
    GREEN_FLAG = "G"
    RED_FLAG = "R"
    YELLOW_F = "1"
    YELLOW_S = "2"
    YELLOW_T = "3"
    YELLOW_FS = "4"
    YELLOW_ST = "5"
    YELLOW_TF = "6"
    WET_RACE = "W"

    # CMD FOR SAFETY
    SAFETY_CAR = "Y"
    FULL_YELLOW = "F"

    PIT_CLOSER = "P"
    PIT_OPEN = "O"
    PIT_VALID = "V"

    END_SESSION = "E"
    CLC = "d"
    CLC_YELLOW = "T"

    PRE_RACE = "p"
    PRE10 = "7"
    PRE5 = "8"
    PRE2 = "9"
    PRE1 = "0"
    FORMATION_LAP = "L"

    STATUS = "A"


def cmd(c: DeviceCommand) -> bytes:
    """
    Utility: converte un comando in bytes (utile per Serial/Socket).
    """
    return c.value.encode("ascii")
