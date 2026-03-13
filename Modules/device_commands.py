from __future__ import annotations
from enum import Enum


class DeviceCommand(str, Enum):
    # ------------------------------------------------------------
    # CONNESSIONE
    # ------------------------------------------------------------
    CMD_CONNECT = "CN"
    CMD_DISCONNECT = "DC"
    CMD_STATUS = "ST"

    # ------------------------------------------------------------
    # BANDIERE BASE
    # ------------------------------------------------------------
    CMD_GREEN = "FG"
    CMD_RED = "FR"
    CMD_BLUE = "FB"
    CMD_WET = "FW"
    CMD_CHECKERED = "FC"

    # ------------------------------------------------------------
    # YELLOW SETTORIALI
    # ------------------------------------------------------------
    CMD_YELLOW_S1 = "Y1"
    CMD_YELLOW_S2 = "Y2"
    CMD_YELLOW_S3 = "Y3"
    CMD_YELLOW_FS = "YF"   # S1 + S2
    CMD_YELLOW_ST = "YS"   # S2 + S3
    CMD_YELLOW_TF = "YT"   # S3 + S1

    # ------------------------------------------------------------
    # BLUE SETTORIALI + PIT
    # ------------------------------------------------------------
    CMD_BLUE_S1 = "B1"
    CMD_BLUE_S2 = "B2"
    CMD_BLUE_S3 = "B3"
    CMD_BLUE_PIT = "BP"    # non usato ma mantenuto

    # ------------------------------------------------------------
    # SAFETY
    # ------------------------------------------------------------
    CMD_SAFETY_CAR = "SC"
    CMD_VIRTUAL_SC = "VS"

    # ------------------------------------------------------------
    # PIT
    # ------------------------------------------------------------
    CMD_PIT_OPEN = "PO"
    CMD_PIT_CLOSE = "PC"
    CMD_PIT_VALID = "PV"
    CMD_PIT_OFF = "PF"

    # ------------------------------------------------------------
    # SEMAFORO
    # ------------------------------------------------------------
    CMD_LIGHTS_OUT = "LO"
    CMD_START_PROC = "SP"
    CMD_FORMATION_LAP = "FL"
    CMD_PRE_RACE = "PR"

    # Countdown pre-gara (equivalenti moderni dei legacy '7','8','9','0')
    CMD_PRE_10 = "P0"   # PRE10_CMD  '7'
    CMD_PRE_5  = "P5"   # PRE5_CMD   '8'
    CMD_PRE_2  = "P2"   # PRE2_CMD   '9'
    CMD_PRE_1  = "P1"   # PRE1_CMD   '0'

    # ------------------------------------------------------------
    # LUCI DI PARTENZA (S1–S5)
    # ------------------------------------------------------------
    CMD_START_LIGHT_1 = "S1"
    CMD_START_LIGHT_2 = "S2"
    CMD_START_LIGHT_3 = "S3"
    CMD_START_LIGHT_4 = "S4"
    CMD_START_LIGHT_5 = "S5"

    # ------------------------------------------------------------
    # SISTEMA
    # ------------------------------------------------------------
    CMD_CLEAR_ALL = "CL"
    CMD_CLEAR_YELLOW = "CY"

    # ------------------------------------------------------------
    # ALIAS LEGACY (retrocompatibilita)
    # ------------------------------------------------------------
    CONN_CMD = CMD_CONNECT
    DSCN_CMD = CMD_DISCONNECT
    CONN = CMD_CONNECT
    DSCN = CMD_DISCONNECT
    STATUS_CMD = CMD_STATUS
    STATUS = CMD_STATUS

    START_PROC_CMD = CMD_START_PROC
    START_CMD = CMD_LIGHTS_OUT

    GREEN_FLAG_CMD = CMD_GREEN
    RED_FLAG_CMD = CMD_RED
    YELLOW_F_CMD = CMD_YELLOW_S1
    YELLOW_S_CMD = CMD_YELLOW_S2
    YELLOW_T_CMD = CMD_YELLOW_S3
    YELLOW_FS_CMD = CMD_YELLOW_FS
    YELLOW_ST_CMD = CMD_YELLOW_ST
    YELLOW_TF_CMD = CMD_YELLOW_TF
    WET_RACE_CMD = CMD_WET
    FAN_CMD = CMD_WET

    SAFETY_CAR_CMD = CMD_SAFETY_CAR
    FULL_YELLOW_CMD = CMD_VIRTUAL_SC

    PIT_CLOSER_CMD = CMD_PIT_CLOSE
    PIT_OPEN_CMD = CMD_PIT_OPEN
    PIT_VALID_CMD = CMD_PIT_VALID

    END_SESSION_CMD = CMD_CHECKERED
    CLC_CMD = CMD_CLEAR_ALL
    CLC_YELLOW_CMD = CMD_CLEAR_YELLOW

    PRE_RACE_CMD = CMD_PRE_RACE
    PRE10_CMD = CMD_PRE_10
    PRE5_CMD = CMD_PRE_5
    PRE2_CMD = CMD_PRE_2
    PRE1_CMD = CMD_PRE_1
    FORMATION_LAP_CMD = CMD_FORMATION_LAP


def cmd(c: DeviceCommand) -> bytes:
    return c.value.encode("ascii")
