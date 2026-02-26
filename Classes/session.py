from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from enum import IntEnum
from typing import Any, Dict, List, Sequence
import json

from Modules.device_commands import DeviceCommand


class SessionTypes(IntEnum):
    Practice = 0
    Qualifying = 1
    Hyperpole = 2
    FRace = 3
    SRace = 4
    ERace = 5


class SessionState(IntEnum):
    Starting = -1
    NotStarted = 0
    Started = 1
    Finished = 2
    Stopped = 3


class PitOpenState(IntEnum):
    Closed = 0
    Open  = 1
    Valid = 2

SESSION_NAMES = ["Free Practice", "Q - Groups", "Q - Hyperpole","R - Feature", "R - Sprint","R - Endurance"]

@dataclass
class Session:
    """
    Session = "contesto" della sessione:
    - tipo, stato, timer
    - pit window e pit state
    - pre-race procedure + comando luci
    - JSON per live timing (equivalente VB SessionToLive)
    """

    session_type: int
    session_status: int = field(init=False)

    # ---- runtime ----
    session_time: int = field(init=False)   # secondi rimanenti
    pit_state: int = PitOpenState.Closed                      # 0 close, 1 open, 2 valid
    pit_on: bool = False                    # flag UI/logica
    sectors_on: bool = False                # settori on/off

    # pre-race
    pre_race_minutes: int = 0
    pre_race_time: int = 0  # secondi (countdown)

    # ---- ruleset (fase 1: hardcoded come nel VB) ----
    qpos: int = 4

    max_session_time: List[int] = field(default_factory=lambda: [
        60 * 60,   # Practice
        8 * 60,    # Qualifying
        3 * 60,    # Hyperpole
        20 * 60,   # FRace
        1 * 60,       #15 * 60,   # SRace
        45 * 60,   # ERace
    ])

    light_down_pre_race_time: List[int] = field(default_factory=lambda: [
        10 * 60, 5 * 60, 2 * 60, 1 * 60, 0
    ])

    pit_valid_times: List[int] = field(default_factory=lambda: [0, 0, 0, 2, 0, 5])
    pit_valid_span_min: int = 2
    pit_open_minutes: List[int] = field(default_factory=lambda: [7, 14, 22, 29, 37])

    feature_points: List[int] = field(default_factory=lambda: [25, 18, 15, 12, 10, 8, 6, 4, 2, 1])
    sprint_points: List[int] = field(default_factory=lambda: [15, 12, 10, 8, 7, 6, 5, 4, 2, 1])
    endur_points: List[int] = field(default_factory=lambda: [50, 40, 32, 26, 22, 20, 16, 12, 10, 8, 4, 2])

    def __post_init__(self) -> None:
        self.session_time = self.max_session_time[int(self.session_type)]
        self.session_status = int(SessionState.Starting) if self.is_race() else int(SessionState.NotStarted)

    # ============================================================
    # BASIC FLAGS
    # ============================================================

    def is_race(self) -> bool:
        """VB CheckRace: race = (SessionType >= 3)"""
        return int(self.session_type) >= int(SessionTypes.FRace)

    def is_endurance(self) -> bool:
        return int(self.session_type) == int(SessionTypes.ERace)

    # ============================================================
    # TIMER FORMATS
    # ============================================================

    def session_timer_mmss(self) -> str:
        """VB SessionTimer: mm:ss"""
        minutes = self.session_time // 60
        seconds = self.session_time % 60
        return f"{minutes:02d}:{seconds:02d}"

    def session_timer_hhmmss(self) -> str:
        """VB SessionToLive: hh:mm:ss (da secondi)"""
        sec = max(0, int(self.session_time))
        td = timedelta(seconds=sec)
        hh = td.seconds // 3600
        mm = (td.seconds % 3600) // 60
        ss = td.seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    # ============================================================
    # PIT WINDOW (VB OpenPit)
    # ============================================================

    def open_pit(self) -> bool:
        """
        VB OpenPit:
        - se PitValidTimes(session_type) > 0:
            passed = MaxSessionTime - SessionTime
            se dentro finestra => pit_state=2 e True
        - altrimenti pit_state=1 e False
        """
        valid_times = int(self.pit_valid_times[int(self.session_type)])
        if valid_times > 0:
            passed = int(self.max_session_time[int(self.session_type)] - self.session_time)

            for i in range(min(valid_times, len(self.pit_open_minutes))):
                start = int(self.pit_open_minutes[i] * 60)
                end = int((self.pit_open_minutes[i] + self.pit_valid_span_min) * 60)

                if start <= passed <= end:
                    self.pit_state = PitOpenState.Valid
                    return True

        self.pit_state = PitOpenState.Open
        return False

    # ============================================================
    # PRE-RACE (VB PreRaceProcedure / PreRaceCommandProc)
    # ============================================================

    def pre_race_procedure(self) -> str:
        """VB PreRaceProcedure: '-mm:ss'"""
        minutes = int(self.pre_race_time // 60)
        seconds = int(self.pre_race_time % 60)
        return f"-{minutes:02d}:{seconds:02d}"

    def pre_race_command_proc(self) -> str:
        """
        VB PreRaceCommandProc:
        - Commands = [PRE10, PRE5, PRE2, PRE1, FORMATION_LAP]
        - se PreRaceTime <= soglia => command = Commands(i)
        """
        commands = [
            DeviceCommands.PRE10_CMD,
            DeviceCommands.PRE5_CMD,
            DeviceCommands.PRE2_CMD,
            DeviceCommands.PRE1_CMD,
            DeviceCommands.FORMATION_LAP_CMD,
        ]
        cmd = DeviceCommands.PRE_RACE_CMD

        for i in range(len(self.light_down_pre_race_time)):
            if self.pre_race_time <= self.light_down_pre_race_time[i]:
                cmd = commands[i]
            else:
                break

        return cmd

    # ============================================================
    # SESSION NAME (VB getSessionName)
    # ============================================================

    def get_session_name(self) -> str:
        st = int(self.session_type)
        if st == int(SessionTypes.Practice):
            return "Practice"
        if st == int(SessionTypes.Qualifying):
            return "Q - Group"
        if st == int(SessionTypes.Hyperpole):
            return "Q - Hyperpole"
        if st == int(SessionTypes.FRace):
            return "R - Feature"
        if st == int(SessionTypes.SRace):
            return "R - Sprint Race"
        if st == int(SessionTypes.ERace):
            return "R - Endurance"
        return "Error"

    def get_state_name(self) -> str:
        st = int(self.session_status)

        if st == int(SessionState.Starting):
            return "Starting"
        if st == int(SessionState.NotStarted):
            return "Not Started"
        if st == int(SessionState.Started):
            return "Live"
        if st == int(SessionState.Finished):
            return "Finished"
        if st == int(SessionState.Stopped):
            return "Red Flag / Stopped"

        return "Unknown"
    
    def get_pit_open_state(self) -> str:
        st = int(self.pit_state)
        
        if st == int(PitOpenState.Open):
            return "Open"
        if st == int(PitOpenState.Closed):
            return "Closed"
        if st == int(PitOpenState.Valid):
            return "Valid"
        
    # ============================================================
    # POINTS (VB getPoints) - opzionale: puoi lasciarlo in RaceManager
    # ============================================================

    def get_points(self, pos: int, best: bool):
        st = int(self.session_type)

        if st == int(SessionTypes.Practice):
            return 0

        if st == int(SessionTypes.Qualifying):
            return "Q" if pos <= self.qpos else 0

        if st == int(SessionTypes.Hyperpole):
            return 3 if pos == 1 else 0

        if st == int(SessionTypes.FRace):
            base = self.feature_points[pos - 1]
            return base + 1 if best else base

        if st == int(SessionTypes.SRace):
            base = self.sprint_points[pos - 1]
            return base + 1 if best else base

        if st == int(SessionTypes.ERace):
            base = self.endur_points[pos - 1]
            return base + 1 if best else base

        return 0

    # ============================================================
    # LIVE OUTPUT (VB SessionToLive)
    # ============================================================

    def to_live_dict(self, index: int = -1) -> Dict[str, Any]:
        """
        VB SessionToLive:
        {
          sessionTime: "hh:mm:ss",
          sessionType: SessionType.ToString(),
          sessionStatus: SessionStatus.ToString(),
          pitOpen: OpenPit(),
          index: -1
        }
        """
        return {
            "sessionTime": self.session_timer_hhmmss(),
            "sessionType": self.get_session_name(),
            "sessionStatus": self.get_state_name(),
            "pitOpen": self.get_pit_open_state(),
            "index": int(index),
        }

    def to_live_json(self, index: int = -1) -> str:
        return json.dumps(self.to_live_dict(index=index), ensure_ascii=False, separators=(",", ":"))
