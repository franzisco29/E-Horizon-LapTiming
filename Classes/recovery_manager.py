from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from Classes.driver import Driver
from Classes.race_list import RaceList
from Classes.race_manager import RaceManager
from Modules.enums import RaceState
from Modules.log_utils import log


def _td_to_sec(value: Any) -> float:
    if isinstance(value, timedelta):
        return float(value.total_seconds())
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _sec_to_td(value: Any) -> timedelta:
    try:
        return timedelta(seconds=float(value or 0.0))
    except Exception:
        return timedelta(0)


def _dt_to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return ""


def _iso_to_dt(value: Any, fallback: Optional[datetime] = None) -> datetime:
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value)
        except Exception:
            pass
    return fallback if isinstance(fallback, datetime) else datetime.now()


class RaceRecoveryStore:
    """Filesystem-backed checkpoints for live race recovery."""

    SCHEMA_VERSION = 1

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path)
        self.recovery_dir = (self.root_path / "Data" / "recovery").resolve()
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        self.current_path = self.recovery_dir / "checkpoint_current.json"
        self.previous_path = self.recovery_dir / "checkpoint_previous.json"
        self.temp_path = self.recovery_dir / "checkpoint_current.tmp"

    def cleanup(self, max_age_hours: int = 24) -> None:
        now_epoch = time.time()
        max_age_sec = max(1, int(max_age_hours)) * 3600

        for p in (self.current_path, self.previous_path):
            if not p.exists():
                continue
            try:
                payload = self._load_json_file(p)
            except Exception:
                continue

            ts = float(payload.get("updatedAtEpoch", 0.0) or 0.0)
            if ts <= 0:
                continue
            if (now_epoch - ts) > max_age_sec:
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass

    def load_latest_recoverable(self, max_age_hours: int = 24) -> Optional[Dict[str, Any]]:
        self.cleanup(max_age_hours=max_age_hours)

        for p in (self.current_path, self.previous_path):
            if not p.exists():
                continue
            try:
                payload = self._load_json_file(p)
            except Exception:
                continue

            if bool(payload.get("cleanClose", False)):
                continue
            if int(payload.get("schemaVersion", 0) or 0) != self.SCHEMA_VERSION:
                continue
            if not isinstance(payload.get("drivers"), list):
                continue
            return payload

        return None

    def save_checkpoint(
        self,
        race_man: RaceManager,
        race_list: RaceList,
        list_id: int,
        reason: str,
        *,
        clean_close: bool = False,
    ) -> bool:
        try:
            payload = self._build_payload(
                race_man=race_man,
                race_list=race_list,
                list_id=list_id,
                reason=reason,
                clean_close=clean_close,
            )
            self._atomic_write(payload)
            return True
        except Exception as ex:
            log(f"[Recovery] save checkpoint error: {ex}")
            return False

    def apply_checkpoint(self, race_man: RaceManager, race_list: RaceList, payload: Dict[str, Any]) -> bool:
        try:
            session_data = payload.get("session", {}) or {}
            rm_data = payload.get("raceManager", {}) or {}
            driver_rows = payload.get("drivers", []) or []

            try:
                race_man.session_type = int(session_data.get("sessionType", race_man.session_type))
            except Exception:
                pass

            try:
                race_man.session_status = int(session_data.get("sessionStatus", race_man.session_status))
            except Exception:
                pass

            race_man.session_time = int(session_data.get("sessionTime", race_man.session_time) or 0)

            try:
                race_man.session.pit_state = int(session_data.get("pitState", race_man.pit_state) or 0)
            except Exception:
                pass

            race_man.session.pit_on = bool(session_data.get("pitOn", False))
            race_man.session.sectors_on = bool(session_data.get("sectorsOn", False))
            race_man.session.pre_race_time = int(session_data.get("preRaceTime", 0) or 0)

            race_man.best_lap_driver = int(rm_data.get("bestLapDriver", 0) or 0)
            race_man.time_over = bool(rm_data.get("timeOver", False))
            race_man.leader_finished = bool(rm_data.get("leaderFinished", False))

            leader_finish_lap = rm_data.get("leaderFinishLap", None)
            race_man.leader_finish_lap = int(leader_finish_lap) if leader_finish_lap is not None else None

            race_man.last_device_detected = {
                int(k): int(v)
                for k, v in (rm_data.get("lastDeviceDetected", {}) or {}).items()
            }

            last_time_detected: Dict[Tuple[int, int], datetime] = {}
            for row in (rm_data.get("lastTimeDetected", []) or []):
                try:
                    num = int(row.get("number", 0))
                    dev = int(row.get("device", 0))
                    when = _iso_to_dt(row.get("time", ""))
                    last_time_detected[(num, dev)] = when
                except Exception:
                    continue
            race_man.last_time_detected = last_time_detected

            by_transponder: Dict[int, Dict[str, Any]] = {}
            for drow in driver_rows:
                try:
                    by_transponder[int(drow.get("transponderNumber", -1))] = drow
                except Exception:
                    continue

            for d in race_list.drivers:
                drow = by_transponder.get(int(getattr(d, "number", -1)))
                if drow is None:
                    continue
                self._apply_driver_state(d, drow)

            race_man.set_session_race_list(race_list)

            try:
                race_man._calculate_delta()
            except Exception:
                pass

            try:
                race_man.best_lap_update()
            except Exception:
                pass

            return True
        except Exception as ex:
            log(f"[Recovery] apply checkpoint error: {ex}")
            return False

    def _build_payload(
        self,
        race_man: RaceManager,
        race_list: RaceList,
        list_id: int,
        reason: str,
        clean_close: bool,
    ) -> Dict[str, Any]:
        now = datetime.now()

        session_payload = {
            "sessionType": int(race_man.session_type),
            "sessionStatus": int(race_man.session_status),
            "sessionTime": int(race_man.session_time),
            "pitState": int(race_man.pit_state),
            "pitOn": bool(race_man.session.pit_on),
            "sectorsOn": bool(race_man.session.sectors_on),
            "preRaceTime": int(getattr(race_man.session, "pre_race_time", 0) or 0),
        }

        rm_payload = {
            "bestLapDriver": int(getattr(race_man, "best_lap_driver", 0) or 0),
            "timeOver": bool(getattr(race_man, "time_over", False)),
            "leaderFinished": bool(getattr(race_man, "leader_finished", False)),
            "leaderFinishLap": getattr(race_man, "leader_finish_lap", None),
            "lastDeviceDetected": {
                str(k): int(v)
                for k, v in (getattr(race_man, "last_device_detected", {}) or {}).items()
            },
            "lastTimeDetected": [
                {
                    "number": int(k[0]),
                    "device": int(k[1]),
                    "time": _dt_to_iso(v),
                }
                for k, v in (getattr(race_man, "last_time_detected", {}) or {}).items()
            ],
        }

        drivers_payload = [self._driver_to_dict(d) for d in race_list.drivers]

        return {
            "schemaVersion": self.SCHEMA_VERSION,
            "updatedAt": now.isoformat(timespec="seconds"),
            "updatedAtEpoch": float(time.time()),
            "reason": str(reason),
            "cleanClose": bool(clean_close),
            "listId": int(list_id),
            "session": session_payload,
            "raceManager": rm_payload,
            "drivers": drivers_payload,
        }

    def _driver_to_dict(self, d: Driver) -> Dict[str, Any]:
        return {
            "driverId": int(d.driver_id),
            "transponderNumber": int(d.number),
            "raceNumber": int(d.race_number),
            "name": str(d.name),
            "surname": str(d.surname),
            "team": str(d.team),
            "raceStatus": int(d.race_status),
            "position": int(d.position),
            "laps": int(d.laps),
            "isFastestDriver": bool(d.isFastestDriver),
            "deltaSec": _td_to_sec(d.delta),
            "leaderDeltaSec": _td_to_sec(d.leader_delta),
            "fastLapSec": _td_to_sec(d.fast_lap),
            "lastLapSec": _td_to_sec(d.last_lap),
            "lapHistorySec": [_td_to_sec(x) for x in d.lap_history],
            "cancelledLaps": [
                {"index": int(idx), "lapSec": _td_to_sec(td)}
                for idx, td in d.cancelled_laps
            ],
            "positionHistory": [int(x) for x in d.position_history],
            "lapsBehind": [int(x) for x in d.laps_behind],
            "timeOnTrackSec": _td_to_sec(d.time_on_track),
            "sectorsSec": [_td_to_sec(x) for x in d.sectors],
            "sectorRaceTime": [_dt_to_iso(x) for x in d.sector_race_time],
            "actualSector": int(d.actual_sector),
            "raceTime": _dt_to_iso(d.race_time),
            "sortTime": _dt_to_iso(d.sort_time),
            "startTime": _dt_to_iso(d.start_time),
            "pitInTimesSec": [_td_to_sec(x) for x in d.pit_in_times],
            "pitTimesSec": [_td_to_sec(x) for x in d.pit_times],
            "pitEnterTime": _dt_to_iso(d.pit_enter_time) if d.pit_enter_time else "",
        }

    def _apply_driver_state(self, d: Driver, row: Dict[str, Any]) -> None:
        try:
            d.race_status = RaceState(int(row.get("raceStatus", int(d.race_status)) or 0))
        except Exception:
            d.race_status = RaceState.NOT_STARTED

        d.position = int(row.get("position", d.position) or 0)
        d.laps = int(row.get("laps", d.laps) or 0)
        d.isFastestDriver = bool(row.get("isFastestDriver", False))

        d.delta = _sec_to_td(row.get("deltaSec", 0.0))
        d.leader_delta = _sec_to_td(row.get("leaderDeltaSec", 0.0))
        d.fast_lap = _sec_to_td(row.get("fastLapSec", 0.0))
        d.last_lap = _sec_to_td(row.get("lastLapSec", 0.0))

        d.lap_history = [_sec_to_td(x) for x in (row.get("lapHistorySec", []) or [])]
        d.cancelled_laps = [
            (int(x.get("index", 0)), _sec_to_td(x.get("lapSec", 0.0)))
            for x in (row.get("cancelledLaps", []) or [])
            if isinstance(x, dict)
        ]

        d.position_history = [int(x) for x in (row.get("positionHistory", []) or [])]
        laps_behind = [int(x) for x in (row.get("lapsBehind", []) or [0, 0])]
        if len(laps_behind) < 2:
            laps_behind = [0, 0]
        d.laps_behind = laps_behind[:2]

        d.time_on_track = _sec_to_td(row.get("timeOnTrackSec", 0.0))
        d.sectors = [_sec_to_td(x) for x in (row.get("sectorsSec", []) or [])][:3]
        while len(d.sectors) < 3:
            d.sectors.append(timedelta(0))

        d.sector_race_time = [
            _iso_to_dt(x, fallback=datetime.min) for x in (row.get("sectorRaceTime", []) or [])
        ][:3]
        while len(d.sector_race_time) < 3:
            d.sector_race_time.append(datetime.min)

        d.actual_sector = int(row.get("actualSector", 1) or 1)

        d.race_time = _iso_to_dt(row.get("raceTime", ""), fallback=datetime.now())
        d.sort_time = _iso_to_dt(row.get("sortTime", ""), fallback=d.race_time)
        d.start_time = _iso_to_dt(row.get("startTime", ""), fallback=d.race_time)

        d.pit_in_times = [_sec_to_td(x) for x in (row.get("pitInTimesSec", []) or [])]
        d.pit_times = [_sec_to_td(x) for x in (row.get("pitTimesSec", []) or [])]

        pit_enter_time = str(row.get("pitEnterTime", "") or "").strip()
        d.pit_enter_time = _iso_to_dt(pit_enter_time) if pit_enter_time else None

    def _load_json_file(self, path: Path) -> Dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid recovery payload")
        return data

    def _atomic_write(self, payload: Dict[str, Any]) -> None:
        self.recovery_dir.mkdir(parents=True, exist_ok=True)

        blob = json.dumps(payload, ensure_ascii=False, indent=2)

        with open(self.temp_path, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(blob)
            fp.flush()
            os.fsync(fp.fileno())

        if self.current_path.exists():
            try:
                if self.previous_path.exists():
                    self.previous_path.unlink(missing_ok=True)
                os.replace(self.current_path, self.previous_path)
            except Exception:
                pass

        os.replace(self.temp_path, self.current_path)
