from __future__ import annotations

from enum import Enum


from enum import Enum


class DeviceCommand(str, Enum):
    # CMD OF CONNECTION & UTILITIES
    CONN_CMD = "C"
    DSCN_CMD = "c"
    FAN_CMD = "W"

    # CMD FOR START
    START_PROC_CMD = "s"
    START_CMD = "S"

    # CMD FOR FLAGS
    GREEN_FLAG_CMD = "G"
    RED_FLAG_CMD = "R"
    YELLOW_F_CMD = "1"
    YELLOW_S_CMD = "2"
    YELLOW_T_CMD = "3"
    YELLOW_FS_CMD = "4"
    YELLOW_ST_CMD = "5"
    YELLOW_TF_CMD = "6"
    WET_RACE_CMD = "W"

    # CMD FOR SAFETY
    SAFETY_CAR_CMD = "Y"
    FULL_YELLOW_CMD = "F"

    PIT_CLOSER_CMD = "P"
    PIT_OPEN_CMD = "O"
    PIT_VALID_CMD = "V"

    END_SESSION_CMD = "E"
    CLC_CMD = "d"
    CLC_YELLOW_CMD = "T"

    PRE_RACE_CMD = "p"
    PRE10_CMD = "7"
    PRE5_CMD = "8"
    PRE2_CMD = "9"
    PRE1_CMD = "0"
    FORMATION_LAP_CMD = "L"

    STATUS_CMD = "A"


def cmd(c: DeviceCommand) -> bytes:
    """
    Utility: converte un comando in bytes (utile per Serial/Socket).
    """
    return c.value.encode("ascii")
