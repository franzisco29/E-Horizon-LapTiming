from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


def _as_timedelta(value: Any) -> timedelta:
    if value is None:
        return timedelta(0)
    if isinstance(value, timedelta):
        return value if value.total_seconds() >= 0 else timedelta(0)
    if isinstance(value, (int, float)):
        try:
            return timedelta(seconds=float(value))
        except Exception:
            return timedelta(0)
    return timedelta(0)


def _td_ms(value: Any) -> int:
    td = _as_timedelta(value)
    return max(0, int(td.total_seconds() * 1000))


def _fmt_td(value: Any) -> str:
    td = _as_timedelta(value)
    ms = max(0, int(td.total_seconds() * 1000))
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


@dataclass
class AnalyticsManager:
    race_man: Any
    last_report_path: Optional[Path] = None

    def generate_analytics_excel(
        self,
        root_path: str,
        analytics_context: Optional[Dict[str, Any]] = None,
    ) -> Path:
        root = Path(root_path)
        out_dir = root / "Analytics"
        out_dir.mkdir(parents=True, exist_ok=True)

        context = dict(analytics_context or {})

        session_name = self._session_name()
        now = datetime.now()
        xlsx_path = out_dir / f"SessionAnalytics_{session_name}_{now:%Y%m%d_%H%M%S}.xlsx"

        drivers = list(getattr(getattr(self.race_man, "session_race_list", None), "drivers", []) or [])
        drivers_sorted = sorted(drivers, key=lambda d: int(getattr(d, "position", 9999) or 9999))

        df_context = self._build_context_df(context, now)
        df_summary = self._build_summary_df(drivers_sorted, context)
        df_summary = self._add_percentiles(df_summary)
        df_laps = self._build_laps_df(drivers_sorted, bool(getattr(self.race_man, "race", False)))
        df_sectors = self._build_sectors_df(drivers_sorted, context)
        df_pits = self._build_pits_df(drivers_sorted)
        df_stints = self._build_stints_df(drivers_sorted, bool(getattr(self.race_man, "race", False)))
        df_kpi = self._build_kpi_df(df_summary)
        df_benchmark = self._build_benchmark_df(df_summary)
        df_ai = self._build_ai_insights_df(df_laps)
        df_ai_driver = self._build_ai_driver_summary_df(df_ai, df_summary, df_stints)

        report_path = out_dir / f"SessionAnalytics_{session_name}_{now:%Y%m%d_%H%M%S}_REPORT.txt"
        report_text = self._build_human_report(
            now=now,
            context=context,
            summary_df=df_summary,
            kpi_df=df_kpi,
            benchmark_df=df_benchmark,
            ai_driver_df=df_ai_driver,
            stints_df=df_stints,
        )
        report_path.write_text(report_text, encoding="utf-8")
        self.last_report_path = report_path

        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df_context.to_excel(writer, sheet_name="session_overview", index=False)
            df_summary.to_excel(writer, sheet_name="vehicles_summary", index=False)
            df_laps.to_excel(writer, sheet_name="laps_raw", index=False)
            df_sectors.to_excel(writer, sheet_name="sectors_raw", index=False)
            df_pits.to_excel(writer, sheet_name="pit_raw", index=False)
            df_stints.to_excel(writer, sheet_name="stints", index=False)
            df_kpi.to_excel(writer, sheet_name="generated_metrics", index=False)
            df_benchmark.to_excel(writer, sheet_name="benchmark_field", index=False)
            df_ai.to_excel(writer, sheet_name="ai_insights", index=False)
            df_ai_driver.to_excel(writer, sheet_name="ai_driver_summary", index=False)

        return xlsx_path

    def _build_human_report(
        self,
        now: datetime,
        context: Dict[str, Any],
        summary_df: pd.DataFrame,
        kpi_df: pd.DataFrame,
        benchmark_df: pd.DataFrame,
        ai_driver_df: pd.DataFrame,
        stints_df: pd.DataFrame,
    ) -> str:
        lines: List[str] = []

        session_name = self._session_name()
        circuit = str(context.get("circuit_name", "") or "n/a")
        weather = str(context.get("weather_state", "") or "n/a")
        track_temp = context.get("track_temp_c", "n/a")
        air_temp = context.get("air_temp_c", "n/a")

        lines.append("E-HORIZON SESSION REPORT")
        lines.append("=" * 72)
        lines.append(f"Generated at: {now:%Y-%m-%d %H:%M:%S}")
        lines.append(f"Session: {session_name}")
        lines.append(f"Circuit: {circuit}")
        lines.append(f"Weather: {weather} | Air: {air_temp} C | Track: {track_temp} C")
        lines.append("")

        lines.append("FIELD SNAPSHOT")
        lines.append("-" * 72)
        if not kpi_df.empty and {"metric", "value"}.issubset(set(kpi_df.columns)):
            kv = {str(r["metric"]): r["value"] for _, r in kpi_df.iterrows()}
            lines.append(f"Vehicles: {int(kv.get('vehicle_count', 0) or 0)}")
            lines.append(f"Total laps: {int(kv.get('total_laps', 0) or 0)}")
            best_field = int(kv.get("field_best_lap_ms", 0) or 0)
            field_avg = int(kv.get("field_avg_of_avg_lap_ms", 0) or 0)
            field_cons = float(kv.get("field_mean_consistency_pct", 0.0) or 0.0)
            lines.append(f"Best lap field: {_fmt_td(timedelta(milliseconds=best_field)) if best_field > 0 else 'n/a'}")
            lines.append(f"Avg lap field: {_fmt_td(timedelta(milliseconds=field_avg)) if field_avg > 0 else 'n/a'}")
            lines.append(f"Mean consistency: {field_cons:.2f}%")
        else:
            lines.append("No KPI available.")
        lines.append("")

        lines.append("TOP BENCHMARK")
        lines.append("-" * 72)
        if benchmark_df.empty:
            lines.append("No benchmark data available.")
        else:
            ranking = benchmark_df.head(5)
            for i, (_, row) in enumerate(ranking.iterrows(), start=1):
                did = int(row.get("driver_id", 0) or 0)
                score = float(row.get("benchmark_score", 0.0) or 0.0)

                drv_name = "Driver"
                best_lap_txt = "n/a"
                consistency_txt = "n/a"
                summary_match = summary_df[summary_df["driver_id"] == did] if (not summary_df.empty and "driver_id" in summary_df.columns) else pd.DataFrame()
                if not summary_match.empty:
                    sr = summary_match.iloc[0]
                    name = str(sr.get("driver_name", "") or "").strip()
                    surname = str(sr.get("driver_surname", "") or "").strip()
                    drv_name = f"{name} {surname}".strip() or drv_name
                    best_lap_txt = str(sr.get("best_lap", "") or "n/a")
                    consistency_txt = f"{float(sr.get('consistency_index_pct', 0.0) or 0.0):.2f}%"

                team = str(row.get("team", "") or "")
                race_n = int(row.get("race_number", 0) or 0)
                lines.append(
                    f"{i}. #{race_n} {drv_name} | Team: {team or 'n/a'} | Score: {score:.2f} | "
                    f"Best: {best_lap_txt} | Consistency: {consistency_txt}"
                )
        lines.append("")

        lines.append("AI DRIVER LABELS")
        lines.append("-" * 72)
        if ai_driver_df.empty:
            lines.append("No AI labels available.")
        else:
            for _, row in ai_driver_df.sort_values(by=["mean_anomaly_score", "anomaly_rate_pct"], ascending=[False, False]).head(8).iterrows():
                did = int(row.get("driver_id", 0) or 0)
                label = str(row.get("driver_ai_label", "n/a") or "n/a")
                an_rate = float(row.get("anomaly_rate_pct", 0.0) or 0.0)
                an_mean = float(row.get("mean_anomaly_score", 0.0) or 0.0)

                drv_name = f"Driver {did}"
                if not summary_df.empty and "driver_id" in summary_df.columns:
                    sm = summary_df[summary_df["driver_id"] == did]
                    if not sm.empty:
                        s0 = sm.iloc[0]
                        name = str(s0.get("driver_name", "") or "").strip()
                        surname = str(s0.get("driver_surname", "") or "").strip()
                        drv_name = f"{name} {surname}".strip() or drv_name

                lines.append(
                    f"- {drv_name}: label={label}, anomaly_rate={an_rate:.2f}%, mean_anomaly={an_mean:.4f}"
                )
        lines.append("")

        lines.append("STINT OVERVIEW")
        lines.append("-" * 72)
        if stints_df.empty:
            lines.append("No stint data available.")
        else:
            stint_labels = stints_df["stint_label"].value_counts(dropna=False).to_dict() if "stint_label" in stints_df.columns else {}
            total_stints = int(len(stints_df))
            stable = int(stint_labels.get("stable", 0) or 0)
            degrading = int(stint_labels.get("degrading", 0) or 0)
            improving = int(stint_labels.get("improving", 0) or 0)
            volatile = int(stint_labels.get("volatile", 0) or 0)
            lines.append(f"Total stints: {total_stints}")
            lines.append(f"Stable: {stable} | Degrading: {degrading} | Improving: {improving} | Volatile: {volatile}")

        lines.append("")
        lines.append("NOTES")
        lines.append("-" * 72)
        lines.append("This report is a quick reading layer of the full analytics workbook.")
        lines.append("Use SessionAnalytics_*.xlsx sheets for detailed raw and computed values.")

        return "\n".join(lines) + "\n"

    def _session_name(self) -> str:
        try:
            raw = str(self.race_man.get_session_name())
        except Exception:
            raw = "SESSION"
        safe = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in raw)
        return safe or "SESSION"

    def _driver_total_time(self, d: Any) -> timedelta:
        tot = _as_timedelta(getattr(d, "time_on_track", None))
        if tot.total_seconds() > 0:
            return tot
        # fallback based on start/sort timestamps if present
        st = getattr(d, "start_time", None)
        so = getattr(d, "sort_time", None)
        try:
            dt = so - st
            if isinstance(dt, timedelta) and dt.total_seconds() > 0:
                return dt
        except Exception:
            pass
        return timedelta(0)

    def _build_context_df(self, context: Dict[str, Any], now: datetime) -> pd.DataFrame:
        rows = [
            {"key": "generated_at", "value": now.strftime("%Y-%m-%d %H:%M:%S")},
            {"key": "session_name", "value": self._session_name()},
            {"key": "session_type", "value": int(getattr(self.race_man, "session_type", -1) or -1)},
            {"key": "session_status", "value": int(getattr(self.race_man, "session_status", -1) or -1)},
            {"key": "is_race", "value": int(bool(getattr(self.race_man, "race", False)))},
            {"key": "is_endurance", "value": int(bool(getattr(self.race_man, "endurance", False)))},
        ]
        for k in [
            "circuit_id",
            "circuit_name",
            "circuit_location",
            "track_length_m",
            "sector1_m",
            "sector2_m",
            "sector3_m",
            "weather_state",
            "air_temp_c",
            "track_temp_c",
            "humidity_pct",
            "wind_kmh",
            "notes",
        ]:
            if k in context:
                rows.append({"key": k, "value": context.get(k)})
        return pd.DataFrame(rows)

    def _build_summary_df(self, drivers: List[Any], context: Dict[str, Any]) -> pd.DataFrame:
        track_len_m = float(context.get("track_length_m", 0.0) or 0.0)
        race_mode = bool(getattr(self.race_man, "race", False))

        rows: List[Dict[str, Any]] = []
        for d in drivers:
            hist = [_as_timedelta(x) for x in (getattr(d, "lap_history", []) or [])]
            valid_hist = [x for x in hist if x.total_seconds() > 0]
            hist_for_stats = valid_hist[1:] if race_mode and len(valid_hist) > 1 else valid_hist

            total = self._driver_total_time(d)
            total_ms = _td_ms(total)
            laps = int(getattr(d, "laps", 0) or 0)

            avg_ms = int(sum(_td_ms(x) for x in hist_for_stats) / len(hist_for_stats)) if hist_for_stats else 0
            med_ms = int(sorted(_td_ms(x) for x in hist_for_stats)[len(hist_for_stats) // 2]) if hist_for_stats else 0
            if hist_for_stats:
                vals = [_td_ms(x) for x in hist_for_stats]
                mean = sum(vals) / len(vals)
                var = sum((v - mean) ** 2 for v in vals) / len(vals)
                std_ms = int(var ** 0.5)
            else:
                std_ms = 0

            consistency = 0.0
            if avg_ms > 0:
                consistency = max(0.0, min(100.0, (1.0 - (std_ms / avg_ms)) * 100.0))

            avg_speed_kmh = 0.0
            if track_len_m > 0 and total.total_seconds() > 0 and laps > 0:
                dist_km = (track_len_m * laps) / 1000.0
                hrs = total.total_seconds() / 3600.0
                if hrs > 0:
                    avg_speed_kmh = dist_km / hrs

            rows.append(
                {
                    "position": int(getattr(d, "position", 0) or 0),
                    "driver_id": int(getattr(d, "driver_id", 0) or 0),
                    "transponder_number": int(getattr(d, "number", 0) or 0),
                    "race_number": int(getattr(d, "race_number", 0) or 0),
                    "driver_name": str(getattr(d, "name", "")),
                    "driver_surname": str(getattr(d, "surname", "")),
                    "team": str(getattr(d, "team", "")),
                    "status": str(getattr(d, "get_status_string")() if hasattr(d, "get_status_string") else ""),
                    "laps": laps,
                    "total_time": _fmt_td(total),
                    "total_time_ms": total_ms,
                    "best_lap": _fmt_td(getattr(d, "fast_lap", timedelta(0))),
                    "best_lap_ms": _td_ms(getattr(d, "fast_lap", timedelta(0))),
                    "last_lap": _fmt_td(getattr(d, "last_lap", timedelta(0))),
                    "last_lap_ms": _td_ms(getattr(d, "last_lap", timedelta(0))),
                    "avg_lap_excl_outlap": _fmt_td(timedelta(milliseconds=avg_ms)) if avg_ms > 0 else "",
                    "avg_lap_ms": avg_ms,
                    "median_lap_excl_outlap": _fmt_td(timedelta(milliseconds=med_ms)) if med_ms > 0 else "",
                    "median_lap_ms": med_ms,
                    "std_dev_lap_ms": std_ms,
                    "consistency_index_pct": round(consistency, 2),
                    "gap": str(getattr(d, "print_delta")(False) if hasattr(d, "print_delta") else ""),
                    "interval": str(getattr(d, "print_delta")(True) if hasattr(d, "print_delta") else ""),
                    "points": self.race_man.get_points(int(getattr(d, "position", 0) or 0), False),
                    "pit_count": max(len(getattr(d, "pit_in_times", []) or []), len(getattr(d, "pit_times", []) or [])),
                    "pit_total_ms": sum(_td_ms(p) for p in (getattr(d, "pit_times", []) or [])),
                    "avg_speed_kmh": round(avg_speed_kmh, 3),
                }
            )

        return pd.DataFrame(rows)

    def _build_laps_df(self, drivers: List[Any], race_mode: bool) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for d in drivers:
            hist = [_as_timedelta(x) for x in (getattr(d, "lap_history", []) or [])]
            for i, lap_td in enumerate(hist, start=1):
                if lap_td.total_seconds() <= 0:
                    continue
                rows.append(
                    {
                        "driver_id": int(getattr(d, "driver_id", 0) or 0),
                        "transponder_number": int(getattr(d, "number", 0) or 0),
                        "race_number": int(getattr(d, "race_number", 0) or 0),
                        "team": str(getattr(d, "team", "")),
                        "lap_index": i,
                        "is_outlap": int(bool(race_mode and i == 1)),
                        "lap_time": _fmt_td(lap_td),
                        "lap_ms": _td_ms(lap_td),
                    }
                )
        return pd.DataFrame(rows)

    def _build_sectors_df(self, drivers: List[Any], context: Dict[str, Any]) -> pd.DataFrame:
        s1_m = float(context.get("sector1_m", 0.0) or 0.0)
        s2_m = float(context.get("sector2_m", 0.0) or 0.0)
        s3_m = float(context.get("sector3_m", 0.0) or 0.0)

        rows: List[Dict[str, Any]] = []
        for d in drivers:
            sectors = list(getattr(d, "sectors", []) or [])
            while len(sectors) < 3:
                sectors.append(timedelta(0))
            s_ms = [_td_ms(sectors[idx]) for idx in range(3)]

            v1 = ((s1_m / (s_ms[0] / 1000.0)) * 3.6) if s1_m > 0 and s_ms[0] > 0 else 0.0
            v2 = ((s2_m / (s_ms[1] / 1000.0)) * 3.6) if s2_m > 0 and s_ms[1] > 0 else 0.0
            v3 = ((s3_m / (s_ms[2] / 1000.0)) * 3.6) if s3_m > 0 and s_ms[2] > 0 else 0.0

            rows.append(
                {
                    "driver_id": int(getattr(d, "driver_id", 0) or 0),
                    "transponder_number": int(getattr(d, "number", 0) or 0),
                    "race_number": int(getattr(d, "race_number", 0) or 0),
                    "team": str(getattr(d, "team", "")),
                    "sector1": _fmt_td(sectors[0]),
                    "sector1_ms": s_ms[0],
                    "sector2": _fmt_td(sectors[1]),
                    "sector2_ms": s_ms[1],
                    "sector3": _fmt_td(sectors[2]),
                    "sector3_ms": s_ms[2],
                    "theoretical_best_lap_ms": sum(ms for ms in s_ms if ms > 0),
                    "sector1_speed_kmh": round(v1, 3),
                    "sector2_speed_kmh": round(v2, 3),
                    "sector3_speed_kmh": round(v3, 3),
                }
            )

        return pd.DataFrame(rows)

    def _build_pits_df(self, drivers: List[Any]) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for d in drivers:
            entries = list(getattr(d, "pit_in_times", []) or [])
            times = list(getattr(d, "pit_times", []) or [])
            count = max(len(entries), len(times))
            for i in range(count):
                e = _as_timedelta(entries[i]) if i < len(entries) else timedelta(0)
                t = _as_timedelta(times[i]) if i < len(times) else timedelta(0)
                rows.append(
                    {
                        "driver_id": int(getattr(d, "driver_id", 0) or 0),
                        "transponder_number": int(getattr(d, "number", 0) or 0),
                        "race_number": int(getattr(d, "race_number", 0) or 0),
                        "team": str(getattr(d, "team", "")),
                        "pit_index": i + 1,
                        "pit_entry_time": _fmt_td(e),
                        "pit_entry_ms": _td_ms(e),
                        "pit_duration": _fmt_td(t),
                        "pit_duration_ms": _td_ms(t),
                    }
                )

        return pd.DataFrame(rows)

    def _build_kpi_df(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        if summary_df.empty:
            return pd.DataFrame(columns=["metric", "value"])

        best_lap_ms = summary_df["best_lap_ms"].replace(0, pd.NA).dropna()
        avg_lap_ms = summary_df["avg_lap_ms"].replace(0, pd.NA).dropna()
        consistency = summary_df["consistency_index_pct"].replace(0, pd.NA).dropna()

        rows = [
            {"metric": "vehicle_count", "value": int(len(summary_df))},
            {"metric": "total_laps", "value": int(summary_df["laps"].sum())},
            {"metric": "field_best_lap_ms", "value": int(best_lap_ms.min()) if not best_lap_ms.empty else 0},
            {"metric": "field_avg_of_avg_lap_ms", "value": int(avg_lap_ms.mean()) if not avg_lap_ms.empty else 0},
            {"metric": "field_mean_consistency_pct", "value": round(float(consistency.mean()), 2) if not consistency.empty else 0.0},
            {"metric": "field_total_pit_count", "value": int(summary_df["pit_count"].sum())},
            {"metric": "field_total_pit_ms", "value": int(summary_df["pit_total_ms"].sum())},
        ]
        return pd.DataFrame(rows)

    def _find_pit_lap_indexes(self, d: Any) -> List[int]:
        laps = [_as_timedelta(x) for x in (getattr(d, "lap_history", []) or [])]
        laps_ms = [_td_ms(x) for x in laps if _td_ms(x) > 0]
        if not laps_ms:
            return []

        cum = []
        acc = 0
        for ms in laps_ms:
            acc += ms
            cum.append(acc)

        pit_entries = sorted(_td_ms(x) for x in (getattr(d, "pit_in_times", []) or []) if _td_ms(x) > 0)
        idxs: List[int] = []
        for p_ms in pit_entries:
            lap_idx = next((i + 1 for i, c in enumerate(cum) if c >= p_ms), len(cum))
            if lap_idx not in idxs:
                idxs.append(lap_idx)

        return sorted(idxs)

    def _compute_slope_ms_per_lap(self, values: List[int]) -> float:
        if len(values) < 2:
            return 0.0
        n = float(len(values))
        x_mean = (n + 1.0) / 2.0
        y_mean = sum(values) / n

        num = 0.0
        den = 0.0
        for i, y in enumerate(values, start=1):
            dx = i - x_mean
            num += dx * (y - y_mean)
            den += dx * dx
        if den <= 0:
            return 0.0
        return num / den

    def _build_stints_df(self, drivers: List[Any], race_mode: bool) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for d in drivers:
            laps_all = [_as_timedelta(x) for x in (getattr(d, "lap_history", []) or [])]
            laps_ms = [_td_ms(x) for x in laps_all if _td_ms(x) > 0]
            if not laps_ms:
                continue

            # outlap excluded for race analytics, as requested.
            start_lap = 2 if race_mode and len(laps_ms) > 1 else 1
            pit_lap_idxs = [p for p in self._find_pit_lap_indexes(d) if p >= start_lap]

            bounds = [start_lap]
            bounds.extend([p + 1 for p in pit_lap_idxs])
            bounds = sorted({b for b in bounds if 1 <= b <= len(laps_ms)})
            if not bounds or bounds[0] != start_lap:
                bounds = [start_lap] + bounds

            stint_ranges: List[tuple[int, int]] = []
            for i, s in enumerate(bounds):
                e = (bounds[i + 1] - 1) if i + 1 < len(bounds) else len(laps_ms)
                if s <= e:
                    stint_ranges.append((s, e))

            if not stint_ranges:
                stint_ranges = [(start_lap, len(laps_ms))]

            for stint_idx, (s, e) in enumerate(stint_ranges, start=1):
                stint_vals = laps_ms[s - 1 : e]
                if not stint_vals:
                    continue
                avg_ms = int(sum(stint_vals) / len(stint_vals))
                if len(stint_vals) > 1:
                    mean = sum(stint_vals) / len(stint_vals)
                    var = sum((v - mean) ** 2 for v in stint_vals) / len(stint_vals)
                    std_ms = int(var ** 0.5)
                else:
                    std_ms = 0

                slope = self._compute_slope_ms_per_lap(stint_vals)
                cv = (std_ms / avg_ms) if avg_ms > 0 else 0.0

                if cv > 0.08:
                    label = "volatile"
                elif slope > 35:
                    label = "degrading"
                elif slope < -20:
                    label = "improving"
                else:
                    label = "stable"

                anomaly = min(1.0, max(0.0, (cv / 0.10) * 0.6 + (abs(slope) / 80.0) * 0.4))

                rows.append(
                    {
                        "driver_id": int(getattr(d, "driver_id", 0) or 0),
                        "race_number": int(getattr(d, "race_number", 0) or 0),
                        "team": str(getattr(d, "team", "")),
                        "stint_index": stint_idx,
                        "lap_start": s,
                        "lap_end": e,
                        "lap_count": len(stint_vals),
                        "avg_lap_ms": avg_ms,
                        "std_lap_ms": std_ms,
                        "pace_slope_ms_per_lap": round(slope, 3),
                        "stint_cv": round(cv, 4),
                        "stint_label": label,
                        "stint_anomaly_score": round(anomaly, 4),
                    }
                )

        return pd.DataFrame(rows)

    def _add_percentiles(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        if summary_df.empty:
            return summary_df

        out = summary_df.copy()

        # Lower is better: use ascending=False after negating to get high percentile = better.
        if "best_lap_ms" in out.columns:
            s = out["best_lap_ms"].where(out["best_lap_ms"] > 0)
            out["best_lap_percentile"] = ((-s).rank(pct=True, method="average") * 100).fillna(0).round(2)

        if "avg_lap_ms" in out.columns:
            s = out["avg_lap_ms"].where(out["avg_lap_ms"] > 0)
            out["avg_lap_percentile"] = ((-s).rank(pct=True, method="average") * 100).fillna(0).round(2)

        if "consistency_index_pct" in out.columns:
            s = out["consistency_index_pct"].where(out["consistency_index_pct"] > 0)
            out["consistency_percentile"] = (s.rank(pct=True, method="average") * 100).fillna(0).round(2)

        if "avg_speed_kmh" in out.columns:
            s = out["avg_speed_kmh"].where(out["avg_speed_kmh"] > 0)
            out["avg_speed_percentile"] = (s.rank(pct=True, method="average") * 100).fillna(0).round(2)

        return out

    def _build_benchmark_df(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        if summary_df.empty:
            return pd.DataFrame(
                columns=[
                    "driver_id",
                    "race_number",
                    "team",
                    "best_lap_percentile",
                    "avg_lap_percentile",
                    "consistency_percentile",
                    "avg_speed_percentile",
                    "benchmark_score",
                ]
            )

        cols = [
            "driver_id",
            "race_number",
            "team",
            "best_lap_percentile",
            "avg_lap_percentile",
            "consistency_percentile",
            "avg_speed_percentile",
        ]
        available = [c for c in cols if c in summary_df.columns]
        out = summary_df[available].copy()

        pcols = [c for c in ["best_lap_percentile", "avg_lap_percentile", "consistency_percentile", "avg_speed_percentile"] if c in out.columns]
        if pcols:
            out["benchmark_score"] = out[pcols].mean(axis=1).round(2)
        else:
            out["benchmark_score"] = 0.0

        return out.sort_values(by=["benchmark_score"], ascending=False).reset_index(drop=True)

    def _build_ai_insights_df(self, laps_df: pd.DataFrame) -> pd.DataFrame:
        if laps_df.empty:
            return pd.DataFrame(
                columns=[
                    "driver_id",
                    "race_number",
                    "lap_index",
                    "lap_ms",
                    "driver_mean_lap_ms",
                    "driver_std_lap_ms",
                    "z_score",
                    "anomaly_score",
                    "anomaly_flag",
                ]
            )

        work = laps_df.copy()
        work = work[(work["lap_ms"] > 0) & (work["is_outlap"] == 0)]
        if work.empty:
            return pd.DataFrame(
                columns=[
                    "driver_id",
                    "race_number",
                    "lap_index",
                    "lap_ms",
                    "driver_mean_lap_ms",
                    "driver_std_lap_ms",
                    "z_score",
                    "anomaly_score",
                    "anomaly_flag",
                ]
            )

        grp = work.groupby("driver_id", dropna=False)["lap_ms"]
        work["driver_mean_lap_ms"] = grp.transform("mean")
        work["driver_std_lap_ms"] = grp.transform("std").fillna(0)

        # z-score robust to zero std.
        work["z_score"] = 0.0
        mask = work["driver_std_lap_ms"] > 0
        work.loc[mask, "z_score"] = (work.loc[mask, "lap_ms"] - work.loc[mask, "driver_mean_lap_ms"]) / work.loc[mask, "driver_std_lap_ms"]

        # Scale |z| to [0,1] using threshold 3 sigma.
        work["anomaly_score"] = (work["z_score"].abs() / 3.0).clip(0, 1).round(4)
        work["anomaly_flag"] = (work["anomaly_score"] >= 0.8).astype(int)

        cols = [
            "driver_id",
            "race_number",
            "team",
            "lap_index",
            "lap_ms",
            "driver_mean_lap_ms",
            "driver_std_lap_ms",
            "z_score",
            "anomaly_score",
            "anomaly_flag",
        ]
        return work[cols].sort_values(by=["anomaly_score", "driver_id", "lap_index"], ascending=[False, True, True]).reset_index(drop=True)

    def _build_ai_driver_summary_df(self, ai_df: pd.DataFrame, summary_df: pd.DataFrame, stints_df: pd.DataFrame) -> pd.DataFrame:
        if summary_df.empty:
            return pd.DataFrame(
                columns=[
                    "driver_id",
                    "race_number",
                    "team",
                    "laps_analyzed",
                    "anomaly_events",
                    "anomaly_rate_pct",
                    "mean_anomaly_score",
                    "max_anomaly_score",
                    "dominant_stint_label",
                    "driver_ai_label",
                ]
            )

        rows: List[Dict[str, Any]] = []
        by_driver_ai: Dict[int, pd.DataFrame] = {}
        if not ai_df.empty and "driver_id" in ai_df.columns:
            for did, g in ai_df.groupby("driver_id", dropna=False):
                by_driver_ai[int(did)] = g

        by_driver_stint: Dict[int, pd.DataFrame] = {}
        if not stints_df.empty and "driver_id" in stints_df.columns:
            for did, g in stints_df.groupby("driver_id", dropna=False):
                by_driver_stint[int(did)] = g

        for _, r in summary_df.iterrows():
            did = int(r.get("driver_id", 0) or 0)
            race_n = int(r.get("race_number", 0) or 0)
            team = str(r.get("team", ""))

            g_ai = by_driver_ai.get(did)
            if g_ai is None or g_ai.empty:
                laps_analyzed = 0
                anomaly_events = 0
                anomaly_rate = 0.0
                mean_an = 0.0
                max_an = 0.0
            else:
                laps_analyzed = int(len(g_ai))
                anomaly_events = int(g_ai["anomaly_flag"].sum())
                anomaly_rate = (anomaly_events / laps_analyzed * 100.0) if laps_analyzed > 0 else 0.0
                mean_an = float(g_ai["anomaly_score"].mean()) if laps_analyzed > 0 else 0.0
                max_an = float(g_ai["anomaly_score"].max()) if laps_analyzed > 0 else 0.0

            g_st = by_driver_stint.get(did)
            dominant_stint_label = "n/a"
            mean_stint_an = 0.0
            if g_st is not None and not g_st.empty:
                dominant_stint_label = str(g_st["stint_label"].mode().iloc[0])
                mean_stint_an = float(g_st["stint_anomaly_score"].mean())

            combined = min(1.0, max(0.0, mean_an * 0.7 + mean_stint_an * 0.3))
            if combined >= 0.70 or anomaly_rate >= 35.0:
                driver_label = "unstable"
            elif dominant_stint_label == "degrading" and combined >= 0.45:
                driver_label = "degrading"
            elif dominant_stint_label == "improving" and combined < 0.45:
                driver_label = "improving"
            else:
                driver_label = "stable"

            rows.append(
                {
                    "driver_id": did,
                    "race_number": race_n,
                    "team": team,
                    "laps_analyzed": laps_analyzed,
                    "anomaly_events": anomaly_events,
                    "anomaly_rate_pct": round(anomaly_rate, 2),
                    "mean_anomaly_score": round(mean_an, 4),
                    "max_anomaly_score": round(max_an, 4),
                    "dominant_stint_label": dominant_stint_label,
                    "driver_ai_label": driver_label,
                }
            )

        out = pd.DataFrame(rows)
        if out.empty:
            return out
        return out.sort_values(by=["mean_anomaly_score", "anomaly_rate_pct"], ascending=[False, False]).reset_index(drop=True)
