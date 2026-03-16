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
    CMD_GREEN = "FG"      # Green globale
    CMD_RED = "FR"
    CMD_BLUE = "FB"
    CMD_WET = "FW"
    CMD_CHECKERED = "FC"

    # ------------------------------------------------------------
    # GREEN SETTORIALI + SPECIALI
    # ------------------------------------------------------------
    CMD_GREEN_S1 = "G1"
    CMD_GREEN_S2 = "G2"
    CMD_GREEN_S3 = "G3"
    CMD_GREEN_FS = "GF"   # S1 + S2
    CMD_GREEN_ST = "GS"   # S2 + S3
    CMD_GREEN_TF = "GT"   # S3 + S1

    # ------------------------------------------------------------
    # YELLOW SETTORIALI
    # ------------------------------------------------------------
    CMD_YELLOW_S1 = "Y1"
    CMD_YELLOW_S2 = "Y2"
    CMD_YELLOW_S3 = "Y3"
    CMD_YELLOW_FS = "YF"
    CMD_YELLOW_ST = "YS"
    CMD_YELLOW_TF = "YT"

    # ------------------------------------------------------------
    # BLUE SETTORIALI + PIT
    # ------------------------------------------------------------
    CMD_BLUE_S1 = "B1"
    CMD_BLUE_S2 = "B2"
    CMD_BLUE_S3 = "B3"
    CMD_BLUE_PIT = "BP"

    # ------------------------------------------------------------
    # CLEAR BLUE SETTORIALI
    # ------------------------------------------------------------
    CMD_CLEAR_BLUE_S1 = "1B"
    CMD_CLEAR_BLUE_S2 = "2B"
    CMD_CLEAR_BLUE_S3 = "3B"

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

    # Countdown pre-gara
    CMD_PRE_10 = "P0"
    CMD_PRE_5  = "P5"
    CMD_PRE_2  = "P2"
    CMD_PRE_1  = "P1"

    # ------------------------------------------------------------
    # LUCI DI PARTENZA
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
    CMD_CLEAR_BLUE = "CB"

    # ------------------------------------------------------------
    # ALIAS LEGACY
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
    BLUE_FLAG_CMD = CMD_BLUE

    GREEN_S1_CMD = CMD_GREEN_S1
    GREEN_S2_CMD = CMD_GREEN_S2
    GREEN_S3_CMD = CMD_GREEN_S3
    GREEN_FS_CMD = CMD_GREEN_FS
    GREEN_ST_CMD = CMD_GREEN_ST
    GREEN_TF_CMD = CMD_GREEN_TF

    YELLOW_F_CMD = CMD_YELLOW_S1
    YELLOW_S_CMD = CMD_YELLOW_S2
    YELLOW_T_CMD = CMD_YELLOW_S3
    YELLOW_FS_CMD = CMD_YELLOW_FS
    YELLOW_ST_CMD = CMD_YELLOW_ST
    YELLOW_TF_CMD = CMD_YELLOW_TF

    BLUE_F_CMD = CMD_BLUE_S1
    BLUE_S_CMD = CMD_BLUE_S2
    BLUE_T_CMD = CMD_BLUE_S3
    BLUE_PIT_CMD = CMD_BLUE_PIT

    WET_RACE_CMD = CMD_WET
    FAN_CMD = CMD_WET

    SAFETY_CAR_CMD = CMD_SAFETY_CAR
    FULL_YELLOW_CMD = CMD_VIRTUAL_SC

    PIT_CLOSER_CMD = CMD_PIT_CLOSE
    PIT_OPEN_CMD = CMD_PIT_OPEN
    PIT_VALID_CMD = CMD_PIT_VALID
    PIT_OFF_CMD = CMD_PIT_OFF

    END_SESSION_CMD = CMD_CHECKERED
    CLC_CMD = CMD_CLEAR_ALL
    CLC_YELLOW_CMD = CMD_CLEAR_YELLOW
    CLC_BLUE_CMD = CMD_CLEAR_BLUE
    CLC_BLUE_S1_CMD = CMD_CLEAR_BLUE_S1
    CLC_BLUE_S2_CMD = CMD_CLEAR_BLUE_S2
    CLC_BLUE_S3_CMD = CMD_CLEAR_BLUE_S3

    PRE_RACE_CMD = CMD_PRE_RACE
    PRE10_CMD = CMD_PRE_10
    PRE5_CMD = CMD_PRE_5
    PRE2_CMD = CMD_PRE_2
    PRE1_CMD = CMD_PRE_1
    FORMATION_LAP_CMD = CMD_FORMATION_LAP

    START_LIGHT_1_CMD = CMD_START_LIGHT_1
    START_LIGHT_2_CMD = CMD_START_LIGHT_2
    START_LIGHT_3_CMD = CMD_START_LIGHT_3
    START_LIGHT_4_CMD = CMD_START_LIGHT_4
    START_LIGHT_5_CMD = CMD_START_LIGHT_5


def cmd(c: DeviceCommand) -> bytes:
    return c.value.encode("ascii")
