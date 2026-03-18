from __future__ import annotations
from enum import Enum


class DeviceCommand(str, Enum):
    # ------------------------------------------------------------
    # CONNESSIONE
    # ------------------------------------------------------------
    CMD_CONNECT    = "CN"
    CMD_DISCONNECT = "DC"
    CMD_STATUS     = "ST"

    # ------------------------------------------------------------
    # BANDIERE BASE
    # ------------------------------------------------------------
    CMD_GREEN      = "FG"   # Green globale (tutti i device)
    CMD_RED        = "FR"
    CMD_BLUE       = "FB"
    CMD_WET        = "FW"
    CMD_CHECKERED  = "FC"

    # ------------------------------------------------------------
    # GREEN SETTORIALI + SPECIALI
    # ------------------------------------------------------------
    # G1/G2/G3 → verde solo nel settore richiesto (solo matrici)
    # GF/GS/GT → esattamente come YF/YS/YT ma in verde
    #   GF → settori 1 + 2
    #   GS → settori 2 + 3
    #   GT → settori 3 + 1
    CMD_GREEN_S1   = "G1"
    CMD_GREEN_S2   = "G2"
    CMD_GREEN_S3   = "G3"
    CMD_GREEN_FS   = "GF"   # S1 + S2
    CMD_GREEN_ST   = "GS"   # S2 + S3
    CMD_GREEN_TF   = "GT"   # S3 + S1

    # ------------------------------------------------------------
    # YELLOW SETTORIALI
    # ------------------------------------------------------------
    CMD_YELLOW_S1  = "Y1"
    CMD_YELLOW_S2  = "Y2"
    CMD_YELLOW_S3  = "Y3"
    CMD_YELLOW_FS  = "YF"   # S1 + S2
    CMD_YELLOW_ST  = "YS"   # S2 + S3
    CMD_YELLOW_TF  = "YT"   # S3 + S1

    # ------------------------------------------------------------
    # BLUE SETTORIALI + PIT
    # ------------------------------------------------------------
    CMD_BLUE_S1    = "B1"
    CMD_BLUE_S2    = "B2"
    CMD_BLUE_S3    = "B3"
    CMD_BLUE_PIT   = "BP"

    # ------------------------------------------------------------
    # SAFETY
    # ------------------------------------------------------------
    CMD_SAFETY_CAR = "SC"
    CMD_VIRTUAL_SC = "VS"

    # ------------------------------------------------------------
    # PIT
    # ------------------------------------------------------------
    CMD_PIT_OPEN   = "PO"
    CMD_PIT_CLOSE  = "PC"
    CMD_PIT_VALID  = "PV"
    CMD_PIT_OFF    = "PF"

    # ------------------------------------------------------------
    # SEMAFORO - START SEQUENCE
    # ------------------------------------------------------------
    CMD_LIGHTS_OUT = "LO"   # Spegne le luci
    CMD_START_PROC = "SP"   # Avvia la sequenza di partenza (accensione S1..S5 ogni 1s, senza random delay)
    CMD_START_AUTO = "SA"   # Sequenza automatica con random delay 0-3s per simulare variabilità reale

    # ------------------------------------------------------------
    # PRE-GARA
    # ------------------------------------------------------------
    CMD_FORMATION_LAP = "FL"
    CMD_PRE_RACE      = "PR"

    # Countdown pre-gara (mapping legacy)
    CMD_PRE_10 = "P0"
    CMD_PRE_5  = "P5"
    CMD_PRE_2  = "P2"
    CMD_PRE_1  = "P1"

    # ------------------------------------------------------------
    # LUCI DI PARTENZA (accensione singola S1–S5)
    # ------------------------------------------------------------
    CMD_START_LIGHT_1 = "S1"
    CMD_START_LIGHT_2 = "S2"
    CMD_START_LIGHT_3 = "S3"
    CMD_START_LIGHT_4 = "S4"
    CMD_START_LIGHT_5 = "S5"

    # ------------------------------------------------------------
    # SISTEMA
    # ------------------------------------------------------------
    CMD_CLEAR_ALL     = "CL"
    CMD_CLEAR_YELLOW  = "CY"
    CMD_CLEAR_BLUE    = "CB"
    CMD_CLEAR_BLUE_S1 = "1B"
    CMD_CLEAR_BLUE_S2 = "2B"
    CMD_CLEAR_BLUE_S3 = "3B"

    # ============================================================
    # ALIAS LEGACY (protocollo storico — compatibilità)
    # ============================================================

    # Connessione
    CONN_CMD  = CMD_CONNECT
    DSCN_CMD  = CMD_DISCONNECT
    CONN      = CMD_CONNECT
    DSCN      = CMD_DISCONNECT
    STATUS_CMD        = CMD_STATUS
    STATUS            = CMD_STATUS
    STATUS_CMD_LEGACY = CMD_STATUS      # 'A' nel protocollo 1-char

    # Start / luci
    LIGHTS_OUT_CMD = CMD_LIGHTS_OUT     # 'S' nel protocollo 1-char
    START_CMD      = CMD_LIGHTS_OUT     # alias alternativo
    START_PROC_CMD = CMD_START_PROC     # 's' nel protocollo 1-char
    START_AUTO_CMD = CMD_START_AUTO

    START_LIGHT_1_CMD = CMD_START_LIGHT_1
    START_LIGHT_2_CMD = CMD_START_LIGHT_2
    START_LIGHT_3_CMD = CMD_START_LIGHT_3
    START_LIGHT_4_CMD = CMD_START_LIGHT_4
    START_LIGHT_5_CMD = CMD_START_LIGHT_5

    # Bandiere base
    GREEN_FLAG_CMD = CMD_GREEN
    RED_FLAG_CMD   = CMD_RED
    BLUE_FLAG_CMD  = CMD_BLUE
    WET_CMD        = CMD_WET            # 'W' nel protocollo 1-char
    WET_RACE_CMD   = CMD_WET
    FAN_CMD        = CMD_WET
    END_SESSION_CMD    = CMD_CHECKERED
    CHECKERED_FLAG_CMD = CMD_CHECKERED

    # Green settoriali
    GREEN_S1_CMD = CMD_GREEN_S1
    GREEN_S2_CMD = CMD_GREEN_S2
    GREEN_S3_CMD = CMD_GREEN_S3
    GREEN_FS_CMD = CMD_GREEN_FS
    GREEN_ST_CMD = CMD_GREEN_ST
    GREEN_TF_CMD = CMD_GREEN_TF
    # alias _CMD espliciti
    GREEN_S1 = CMD_GREEN_S1
    GREEN_S2 = CMD_GREEN_S2
    GREEN_S3 = CMD_GREEN_S3
    GREEN_FS = CMD_GREEN_FS
    GREEN_ST = CMD_GREEN_ST
    GREEN_TF = CMD_GREEN_TF

    # Yellow settoriali
    YELLOW_F_CMD  = CMD_YELLOW_S1
    YELLOW_S_CMD  = CMD_YELLOW_S2
    YELLOW_T_CMD  = CMD_YELLOW_S3
    YELLOW_FS_CMD = CMD_YELLOW_FS
    YELLOW_ST_CMD = CMD_YELLOW_ST
    YELLOW_TF_CMD = CMD_YELLOW_TF

    # Blue settoriali
    BLUE_F_CMD   = CMD_BLUE_S1
    BLUE_S_CMD   = CMD_BLUE_S2
    BLUE_T_CMD   = CMD_BLUE_S3
    BLUE_PIT_CMD = CMD_BLUE_PIT
    BLUE_PIT     = CMD_BLUE_PIT

    # Safety
    SAFETY_CAR_CMD  = CMD_SAFETY_CAR
    VIRTUAL_SC_CMD  = CMD_VIRTUAL_SC
    FULL_YELLOW_CMD = CMD_VIRTUAL_SC    # 'F' nel protocollo 1-char

    # Pit
    PIT_CLOSER_CMD = CMD_PIT_CLOSE
    PIT_OPEN_CMD   = CMD_PIT_OPEN
    PIT_VALID_CMD  = CMD_PIT_VALID
    PIT_OFF_CMD    = CMD_PIT_OFF
    PIT_OFF        = CMD_PIT_OFF

    # Pre-gara
    PRE_RACE_CMD      = CMD_PRE_RACE
    PRE10_CMD         = CMD_PRE_10
    PRE5_CMD          = CMD_PRE_5
    PRE2_CMD          = CMD_PRE_2
    PRE1_CMD          = CMD_PRE_1
    FORMATION_LAP_CMD = CMD_FORMATION_LAP

    # Clear
    CLC_CMD          = CMD_CLEAR_ALL
    CLC_YELLOW_CMD   = CMD_CLEAR_YELLOW
    CLC_BLUE_CMD     = CMD_CLEAR_BLUE
    CLC_BLUE_S1_CMD  = CMD_CLEAR_BLUE_S1
    CLC_BLUE_S2_CMD  = CMD_CLEAR_BLUE_S2
    CLC_BLUE_S3_CMD  = CMD_CLEAR_BLUE_S3
    CLEAR_BLUE_S1_CMD = CMD_CLEAR_BLUE_S1
    CLEAR_BLUE_S2_CMD = CMD_CLEAR_BLUE_S2
    CLEAR_BLUE_S3_CMD = CMD_CLEAR_BLUE_S3

    # Speciali legacy senza equivalente diretto nel nuovo protocollo
    BRIEFING_CMD = CMD_STATUS           # 'b' nel protocollo 1-char
    MENU_CMD     = CMD_STATUS           # 'M' nel protocollo 1-char


def cmd(c: DeviceCommand) -> bytes:
    """Restituisce il valore del comando come bytes ASCII."""
    return c.value.encode("ascii")