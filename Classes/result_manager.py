from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


# ----------------------------
# Helpers formatting
# ----------------------------
def _coerce_timedelta(value: Any, driver: Any = None) -> timedelta:
    """Convert runtime timing values to a duration.

    Driver fields may be either timedelta (durations) or datetime timestamps.
    """
    if value is None:
        return timedelta(0)

    if isinstance(value, timedelta):
        return value

    if isinstance(value, datetime):
        start = getattr(driver, "start_time", None) if driver is not None else None
        if isinstance(start, datetime):
            dt = value - start
            if dt.total_seconds() >= 0:
                return dt
        return timedelta(0)

    if isinstance(value, (int, float)):
        try:
            return timedelta(seconds=float(value))
        except Exception:
            return timedelta(0)

    return timedelta(0)


def fmt_mm_ss_mmm(value: Any, driver: Any = None) -> str:
    td = _coerce_timedelta(value, driver=driver)
    total_ms = int(td.total_seconds() * 1000)
    if total_ms < 0:
        total_ms = 0
    minutes = total_ms // 60000
    seconds = (total_ms % 60000) // 1000
    millis = total_ms % 1000
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


def fmt_m_ss_mmm(value: Any, driver: Any = None) -> str:
    # per lap history usa m:ss.fff
    td = _coerce_timedelta(value, driver=driver)
    total_ms = int(td.total_seconds() * 1000)
    if total_ms < 0:
        total_ms = 0
    minutes = total_ms // 60000
    seconds = (total_ms % 60000) // 1000
    millis = total_ms % 1000
    return f"{minutes}:{seconds:02d}.{millis:03d}"


@dataclass
class ResultManager:
    race_man: Any
    event_name: str = "E-HORIZON CHAMPIONSHIP"
    logo_path: Optional[str] = None  # es: "resources/logo.png"
    _penalty_seconds_by_number: Dict[int, int] = None

    # ----------------------------
    # Public API
    # ----------------------------
    def generate_result_pdf(self, root_path: str, penalties: Optional[List[Dict[str, Any]]] = None) -> Path:
        """
        VB: GenerateResultPDF()
        Crea PDF in <root_path>/Results/Results <session> <date>.pdf
        + salva RAW json.
        """
        if not self.event_name:
            self.event_name = "E-HORIZON CHAMPIONSHIP"

        self._penalty_seconds_by_number = self._build_penalty_seconds_map(penalties)

        session = self._get_session_name()
        results_dir = Path(root_path) / "Results"
        results_dir.mkdir(parents=True, exist_ok=True)

        filename = results_dir / f"Results {session} {datetime.now():%d-%m-%Y %H-%M}.pdf"

        c = canvas.Canvas(str(filename), pagesize=A4)
        page_w, page_h = A4

        # Intro page
        self._add_intro_page(c, title="Race Result", filename=filename.name, session=session)
        c.showPage()

        # Main page
        y = page_h - 20 * mm

        # Logo center
        y = self._draw_logo_centered(c, page_w, y, max_w=35 * mm, max_h=35 * mm)

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(page_w / 2, y, f"{self.event_name} - {session} Classification")
        y -= 10 * mm
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(page_w / 2, y, "Race Provisional Classification")
        y -= 10 * mm

        # Table headers
        headers = ["POS", "DRIVER", "TEAM", "LAPS", "TIME", "GAP", "INT", "FASTEST", "PTS"]

        if not self.race_man.race:
            headers[4], headers[7] = headers[7], headers[4]
        else:
            if getattr(self.race_man, "endurance", False):
                headers[1] = "DRIVERS"

        col_w = [10 * mm, 48 * mm, 34 * mm, 12 * mm, 18 * mm, 16 * mm, 16 * mm, 18 * mm, 10 * mm]
        x = self._centered_x_positions(page_w, col_w)

        c.setFont("Helvetica", 8.5)
        for i, h in enumerate(headers):
            c.drawString(x[i], y, h)
        y -= 6 * mm

        # Best lap driver for bonus points / fastest lap block
        best_lap_drv = self._find_best_lap_driver()

        # Rows
        drivers = list(self.race_man.session_race_list.drivers)
        drivers_sorted = sorted(drivers, key=lambda d: d.position)

        c.setFont("Helvetica", 8.5)
        for drv in drivers_sorted:
            if y < 25 * mm:
                c.showPage()
                y = page_h - 20 * mm

            c.drawString(x[0], y, str(drv.position))

            # Driver name column
            if getattr(self.race_man, "endurance", False):
                # VB: find roadster containing transponder number
                roadsters = getattr(self.race_man.session_race_list, "roadsters", None) or []
                idx = next((r for r in roadsters if drv.number in r.numbers), None)
                name_txt = idx.to_result() if idx else drv.name_surname()
            else:
                name_txt = drv.name_surname()

            c.drawString(x[1], y, name_txt)

            # Team shortened
            c.drawString(x[2], y, self._shorten_team_name(drv.team))
            c.drawString(x[3], y, str(drv.laps))

            if self.race_man.race:
                c.drawString(x[4], y, fmt_mm_ss_mmm(self._driver_total_time(drv), driver=drv))
            else:
                # In non-race, column 4 is FASTEST after header swap.
                c.drawString(x[4], y, fmt_mm_ss_mmm(drv.fast_lap))

            c.drawString(x[5], y, drv.print_delta(False))
            c.drawString(x[6], y, drv.print_delta(True))

            if self.race_man.race:
                c.drawString(x[7], y, fmt_mm_ss_mmm(drv.fast_lap))
            else:
                # In non-race, column 7 is TIME after header swap.
                c.drawString(x[7], y, fmt_mm_ss_mmm(self._driver_total_time(drv), driver=drv))

            best = bool(self.race_man.race and best_lap_drv and best_lap_drv.number == drv.number)
            pts = self.race_man.get_points(drv.position, best)
            c.drawString(x[8], y, str(pts))

            y -= 6 * mm

        y -= 8 * mm

        table_w = sum(col_w)

        # Fastest lap block
        if best_lap_drv is not None and self.race_man.race:
            if y < 40 * mm:
                c.showPage()
                y = page_h - 20 * mm

            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(x[0] + table_w / 2, y, "FASTEST LAP")
            y -= 6 * mm
            c.setFont("Helvetica", 9)
            c.drawCentredString(
                x[0] + table_w / 2,
                y,
                best_lap_drv.fst_lap_to_res(getattr(self.race_man, "endurance", False)),
            )
            y -= 12 * mm

        # Footer
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        c.setFont("Helvetica", 7)
        c.drawString(15 * mm, 12 * mm, "Approved by General Director E-Horizon Francesco Troianiello")
        c.drawRightString(page_w - 15 * mm, 12 * mm, date_str)

        self._add_lap_history_pages(c, page_w, page_h, drivers)

        # Dedicated pit log pages (chronological) only if pit system is enabled.
        if self._pit_log_enabled():
            self._add_pit_log_pages(c, page_w, page_h, drivers)

        if penalties:
            self._add_penalty_page(c, page_w, page_h, penalties)

        c.save()

        # Save RAW
        self.save_raw_data(root_path=str(Path(root_path)), pdf_filename=str(filename))

        return filename

    def generate_lap_history_pdf(self, root_path: str) -> Path:
        """
        VB: GenerateLapHistoryPDF()
        """
        drivers = list(self.race_man.session_race_list.drivers)

        doc_path = Path(root_path) / f"LapHistory_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        c = canvas.Canvas(str(doc_path), pagesize=A4)
        page_w, page_h = A4

        self._add_lap_history_pages(c, page_w, page_h, drivers)

        c.save()
        return doc_path

    def save_raw_data(self, root_path: str, pdf_filename: str) -> Path:
        """
        VB: SaveRawData(raceManager, filename)
        filename -> result_json json con stesso nome base.
        """
        raw_dir = Path(root_path) / "result_json"
        raw_dir.mkdir(parents=True, exist_ok=True)

        # base filename (senza estensione)
        base = Path(pdf_filename).stem.replace("Results", "result_json")
        raw_filename = raw_dir / f"{base}.json"

        rm = self.race_man
        best_lap_drv = self._find_best_lap_driver()

        data: Dict[str, Any] = {}
        data["sessionType"] = str(getattr(rm, "session_type", ""))
        data["date"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        driver_list: List[Dict[str, Any]] = []
        for d in rm.session_race_list.drivers:
            driver_data: Dict[str, Any] = {}
            driver_data["name"] = d.name
            driver_data["surname"] = d.surname
            driver_data["number"] = d.race_number
            driver_data["transponderNumber"] = d.number
            driver_data["team"] = d.team
            driver_data["laps"] = d.laps
            driver_data["history"] = [fmt_mm_ss_mmm(ts) for ts in d.lap_history]
            driver_data["bestLap"] = fmt_mm_ss_mmm(d.fast_lap)
            driver_data["position"] = d.position
            driver_data["totalTime"] = fmt_mm_ss_mmm(self._driver_total_time(d), driver=d)
            driver_data["interval"] = d.print_delta(True)
            driver_data["leader"] = d.print_delta(False)
            driver_data["entryPitTimes"] = [fmt_mm_ss_mmm(ts) for ts in d.pit_in_times]
            driver_data["pitTimes"] = [fmt_mm_ss_mmm(ts) for ts in d.pit_times]

            best = bool(rm.race and best_lap_drv and best_lap_drv.number == d.number)
            driver_data["points"] = rm.get_points(d.position, best)
            driver_data["penaltySeconds"] = int((self._penalty_seconds_by_number or {}).get(int(d.number), 0))

            driver_list.append(driver_data)

        data["drivers"] = driver_list

        raw_filename.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return raw_filename

    # ----------------------------
    # Internals
    # ----------------------------
    def _get_session_name(self) -> str:
        if hasattr(self.race_man, "get_session_name"):
            return self.race_man.get_session_name()
        if hasattr(self.race_man, "session_name"):
            return str(self.race_man.session_name)
        return "SESSION"

    def _shorten_team_name(self, name: str) -> str:
        if not name:
            return ""
        return (name[:15] + "…") if len(name) > 16 else name

    def _driver_total_time(self, driver: Any) -> timedelta:
        """Best-effort total race time for exports.

        Prefer explicit duration if available, otherwise derive from race_time/start_time.
        """
        total = _coerce_timedelta(getattr(driver, "time_on_track", None), driver=driver)
        if total.total_seconds() > 0:
            return total
        return _coerce_timedelta(getattr(driver, "race_time", None), driver=driver)

    def _pit_log_enabled(self) -> bool:
        session = getattr(self.race_man, "session", None)
        return bool(getattr(self.race_man, "race", False) and getattr(session, "pit_on", False))

    def _build_penalty_seconds_map(self, penalties: Optional[List[Dict[str, Any]]]) -> Dict[int, int]:
        out: Dict[int, int] = {}
        if not penalties:
            return out

        for row in penalties:
            try:
                number = int(row.get("driver_number", 0) or 0)
            except Exception:
                number = 0

            try:
                sec = int(row.get("seconds", 0) or 0)
            except Exception:
                sec = 0

            if number <= 0 or sec <= 0:
                continue
            out[number] = out.get(number, 0) + sec

        return out

    def _add_lap_history_pages(self, c: canvas.Canvas, page_w: float, page_h: float, drivers: List[Any]) -> None:
        all_drivers = sorted(drivers, key=lambda d: d.number)
        if not all_drivers:
            return

        drivers_per_page = 5
        margin_x = 15 * mm
        lap_col_w = 18 * mm
        row_h = 6.5 * mm
        usable_w = page_w - (2 * margin_x)

        pages = (len(all_drivers) + drivers_per_page - 1) // drivers_per_page

        def draw_page_header() -> float:
            y = page_h - 18 * mm
            y = self._draw_logo_centered(c, page_w, y, max_w=25 * mm, max_h=25 * mm)

            c.setFont("Helvetica-Bold", 15)
            c.drawCentredString(page_w / 2, y, f"{self.event_name} - LAP HISTORY")
            y -= 7 * mm

            c.setFont("Helvetica", 9)
            c.drawCentredString(page_w / 2, y, f"{self._get_session_name()} | {datetime.now():%d/%m/%Y %H:%M}")
            return y - 10 * mm

        for page_index in range(pages):
            c.showPage()
            y = draw_page_header()

            drivers_this_page = all_drivers[page_index * drivers_per_page:(page_index + 1) * drivers_per_page]
            driver_count = len(drivers_this_page)
            if driver_count == 0:
                continue

            best_laps = [min(d.lap_history) if d.lap_history else timedelta.max for d in drivers_this_page]
            max_laps = max((len(d.lap_history) for d in drivers_this_page), default=0)
            driver_col_w = (usable_w - lap_col_w) / driver_count

            table_x = margin_x
            table_y_top = y
            total_rows = max_laps + 1
            table_h = total_rows * row_h
            table_y_bottom = table_y_top - table_h

            c.setLineWidth(0.5)

            # Outer border
            c.rect(table_x, table_y_bottom, usable_w, table_h, stroke=1, fill=0)

            # Vertical grid lines
            c.line(table_x + lap_col_w, table_y_bottom, table_x + lap_col_w, table_y_top)
            for idx in range(1, driver_count):
                xpos = table_x + lap_col_w + (idx * driver_col_w)
                c.line(xpos, table_y_bottom, xpos, table_y_top)

            # Horizontal grid lines
            for row_idx in range(1, total_rows):
                ypos = table_y_top - (row_idx * row_h)
                c.line(table_x, ypos, table_x + usable_w, ypos)

            # Header row
            header_y = table_y_top - (row_h * 0.72)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawCentredString(table_x + (lap_col_w / 2), header_y, "LAP")
            for idx, drv in enumerate(drivers_this_page):
                cell_x = table_x + lap_col_w + (idx * driver_col_w)
                c.drawCentredString(cell_x + (driver_col_w / 2), header_y, self._lap_history_driver_label(drv))

            current_y = table_y_top - row_h - (row_h * 0.72)
            for lap_index in range(max_laps):
                c.setFont("Helvetica", 8.3)
                c.drawCentredString(table_x + (lap_col_w / 2), current_y, str(lap_index + 1))

                for drv_idx, drv in enumerate(drivers_this_page):
                    lap_str = ""
                    font_name = "Helvetica"
                    if lap_index < len(drv.lap_history):
                        lap_time = drv.lap_history[lap_index]
                        lap_str = fmt_m_ss_mmm(lap_time)
                        if lap_time == best_laps[drv_idx]:
                            font_name = "Helvetica-Bold"

                    c.setFont(font_name, 8.3)
                    cell_x = table_x + lap_col_w + (drv_idx * driver_col_w)
                    c.drawCentredString(cell_x + (driver_col_w / 2), current_y, lap_str)

                current_y -= row_h

            c.setFont("Helvetica", 7)
            c.drawString(15 * mm, 12 * mm, "Approved by General Director E-Horizon Francesco Troianiello")
            c.drawRightString(page_w - 15 * mm, 12 * mm, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def _driver_display_name(self, drv: Any) -> str:
        if getattr(self.race_man, "endurance", False):
            roadsters = getattr(self.race_man.session_race_list, "roadsters", None) or []
            rd = next((r for r in roadsters if drv.number in r.numbers), None)
            return rd.to_result() if rd else drv.name_surname()
        return drv.name_surname()

    def _lap_history_driver_label(self, drv: Any) -> str:
        surname = str(getattr(drv, "surname", "")).strip()
        race_number = int(getattr(drv, "race_number", 0) or 0)
        if surname:
            return f"#{race_number:02d} {surname}"
        return f"#{race_number:02d}"

    def _collect_pit_events(self, drivers: List[Any]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        for drv in drivers:
            entries = list(getattr(drv, "pit_in_times", []) or [])
            durations = list(getattr(drv, "pit_times", []) or [])

            for idx, entry in enumerate(entries):
                entry_td = _coerce_timedelta(entry, driver=drv)
                pit_td = _coerce_timedelta(durations[idx], driver=drv) if idx < len(durations) else timedelta(0)

                events.append(
                    {
                        "entry": entry_td,
                        "driver": self._driver_display_name(drv),
                        "team": self._shorten_team_name(getattr(drv, "team", "")),
                        "pit_time": pit_td,
                    }
                )

        events.sort(key=lambda e: e["entry"])
        return events

    def _add_pit_log_pages(self, c: canvas.Canvas, page_w: float, page_h: float, drivers: List[Any]) -> None:
        events = self._collect_pit_events(drivers)
        if not events:
            return

        col_w = [14 * mm, 26 * mm, 58 * mm, 40 * mm, 28 * mm]
        x = self._centered_x_positions(page_w, col_w)
        headers = ["#", "PIT IN", "DRIVER", "TEAM", "PIT TIME"]

        def draw_header(y_val: float) -> float:
            y_logo = self._draw_logo_centered(c, page_w, y_val, max_w=25 * mm, max_h=25 * mm)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(page_w / 2, y_logo, f"{self.event_name} - PIT LOG")
            y_logo -= 7 * mm

            c.setFont("Helvetica", 9)
            c.drawCentredString(page_w / 2, y_logo, f"{self._get_session_name()} | {datetime.now():%d/%m/%Y %H:%M}")
            y_logo -= 10 * mm

            c.setFont("Helvetica-Bold", 8.5)
            for i, h in enumerate(headers):
                c.drawString(x[i], y_logo, h)
            return y_logo - 6 * mm

        c.showPage()
        y = draw_header(page_h - 20 * mm)

        c.setFont("Helvetica", 8.5)
        for idx, ev in enumerate(events, start=1):
            if y < 20 * mm:
                c.showPage()
                y = draw_header(page_h - 20 * mm)
                c.setFont("Helvetica", 8.5)

            c.drawString(x[0], y, str(idx))
            c.drawString(x[1], y, fmt_mm_ss_mmm(ev["entry"]))
            c.drawString(x[2], y, str(ev["driver"]))
            c.drawString(x[3], y, str(ev["team"]))
            c.drawString(x[4], y, fmt_mm_ss_mmm(ev["pit_time"]))
            y -= 6 * mm

        c.setFont("Helvetica", 7)
        c.drawString(15 * mm, 12 * mm, "Approved by General Director E-Horizon Francesco Troianiello")
        c.drawRightString(page_w - 15 * mm, 12 * mm, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def _add_penalty_page(
        self,
        c: canvas.Canvas,
        page_w: float,
        page_h: float,
        penalties: List[Dict[str, Any]],
    ) -> None:
        if not penalties:
            return

        detail_col_w = [58 * mm, 20 * mm, 100 * mm]
        detail_x = self._centered_x_positions(page_w, detail_col_w)
        detail_headers = ["PILOTA", "PEN.(s)", "MOTIVAZIONE"]

        summary_col_w = [58 * mm, 22 * mm, 24 * mm, 46 * mm]
        summary_x = self._centered_x_positions(page_w, summary_col_w)
        summary_headers = ["PILOTA", "TOT PEN.(s)", "MEDIA", "CONVERSIONE"]

        def draw_header(y_val: float) -> float:
            y_logo = self._draw_logo_centered(c, page_w, y_val, max_w=25 * mm, max_h=25 * mm)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(page_w / 2, y_logo, f"{self.event_name} - PENALITA'")
            y_logo -= 7 * mm

            c.setFont("Helvetica", 9)
            c.drawCentredString(page_w / 2, y_logo, f"{self._get_session_name()} | {datetime.now():%d/%m/%Y %H:%M}")
            y_logo -= 10 * mm

            return y_logo - 6 * mm

        c.showPage()
        y = draw_header(page_h - 20 * mm)

        # --- Sezione 1: dettaglio penalita e motivazioni ---
        c.setFont("Helvetica-Bold", 9)
        c.drawString(detail_x[0], y, "Dettaglio penalita")
        y -= 6 * mm

        c.setFont("Helvetica-Bold", 8.5)
        for i, h in enumerate(detail_headers):
            c.drawString(detail_x[i], y, h)
        y -= 6 * mm

        c.setFont("Helvetica", 8.5)
        for row in penalties:
            if y < 38 * mm:
                c.showPage()
                y = draw_header(page_h - 20 * mm)

                c.setFont("Helvetica-Bold", 9)
                c.drawString(detail_x[0], y, "Dettaglio penalita")
                y -= 6 * mm

                c.setFont("Helvetica-Bold", 8.5)
                for i, h in enumerate(detail_headers):
                    c.drawString(detail_x[i], y, h)
                y -= 6 * mm

                c.setFont("Helvetica", 8.5)

            driver_name = str(row.get("driver_name", ""))
            sec = str(row.get("seconds", ""))
            motivation = str(row.get("motivation", ""))

            c.drawString(detail_x[0], y, driver_name)
            c.drawString(detail_x[1], y, sec)
            c.drawString(detail_x[2], y, motivation)
            y -= 6 * mm

        # --- Sezione 2: sommatorie per pilota ---
        aggregates: Dict[str, Dict[str, str]] = {}
        for row in penalties:
            driver_name = str(row.get("driver_name", ""))
            sec_val = int(row.get("seconds", 0) or 0)
            avg_lap = str(row.get("avg_lap", "-"))
            conversion = str(row.get("lap_penalty", "-"))
            if driver_name not in aggregates:
                aggregates[driver_name] = {
                    "seconds": "0",
                    "avg_lap": avg_lap,
                    "conversion": conversion,
                }
            total = int(aggregates[driver_name]["seconds"]) + sec_val
            aggregates[driver_name]["seconds"] = str(total)
            aggregates[driver_name]["avg_lap"] = avg_lap
            aggregates[driver_name]["conversion"] = conversion

        if y < 52 * mm:
            c.showPage()
            y = draw_header(page_h - 20 * mm)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(summary_x[0], y, "Riepilogo conversione")
        y -= 6 * mm

        c.setFont("Helvetica-Bold", 8.5)
        for i, h in enumerate(summary_headers):
            c.drawString(summary_x[i], y, h)
        y -= 6 * mm

        c.setFont("Helvetica", 8.5)
        for driver_name in sorted(aggregates.keys()):
            if y < 26 * mm:
                c.showPage()
                y = draw_header(page_h - 20 * mm)

                c.setFont("Helvetica-Bold", 9)
                c.drawString(summary_x[0], y, "Riepilogo conversione")
                y -= 6 * mm

                c.setFont("Helvetica-Bold", 8.5)
                for i, h in enumerate(summary_headers):
                    c.drawString(summary_x[i], y, h)
                y -= 6 * mm

                c.setFont("Helvetica", 8.5)

            row_sum = aggregates[driver_name]
            c.drawString(summary_x[0], y, driver_name)
            c.drawString(summary_x[1], y, row_sum["seconds"])
            c.drawString(summary_x[2], y, row_sum["avg_lap"])
            c.drawString(summary_x[3], y, row_sum["conversion"])
            y -= 6 * mm

        if y < 24 * mm:
            c.showPage()
            y = page_h - 24 * mm

        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(
            15 * mm,
            y,
            "Disclaimer: conversione penalita = floor(penalita_secondi / media_giro).",
        )
        y -= 4 * mm
        c.drawString(
            15 * mm,
            y,
            "Vengono applicati i giri interi risultanti; al tempo si applicano solo i secondi residui.",
        )

        c.setFont("Helvetica", 7)
        c.drawString(15 * mm, 12 * mm, "Approved by General Director E-Horizon Francesco Troianiello")
        c.drawRightString(page_w - 15 * mm, 12 * mm, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def _centered_x_positions(self, page_w: float, col_w: List[float]) -> List[float]:
        total = sum(col_w)
        offset = (page_w - total) / 2
        xs = []
        cur = offset
        for w in col_w:
            xs.append(cur)
            cur += w
        return xs

    def _draw_logo_centered(self, c: canvas.Canvas, page_w: float, y: float, max_w: float, max_h: float) -> float:
        if not self.logo_path:
            return y

        p = Path(self.logo_path)
        if not p.exists():
            return y

        try:
            # reportlab drawImage richiede dimensioni; non sappiamo ratio -> usiamo max_w/max_h
            draw_w = max_w
            draw_h = max_h
            x = (page_w - draw_w) / 2
            c.drawImage(str(p), x, y - draw_h, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
            return y - draw_h - 4 * mm
        except Exception:
            return y

    def _add_intro_page(self, c: canvas.Canvas, title: str, filename: str, session: str) -> None:
        page_w, page_h = A4

        # logos left/right if available
        if self.logo_path and Path(self.logo_path).exists():
            try:
                c.drawImage(self.logo_path, 15 * mm, page_h - 25 * mm, width=20 * mm, height=20 * mm, mask="auto")
                c.drawImage(self.logo_path, page_w - 35 * mm, page_h - 25 * mm, width=20 * mm, height=20 * mm, mask="auto")
            except Exception:
                pass

        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(page_w / 2, page_h - 45 * mm, self.event_name)

        c.setFont("Helvetica", 12)
        c.drawCentredString(page_w / 2, page_h - 55 * mm, f"{session} - {datetime.now():%A %d %B %Y}")

        # line
        c.setLineWidth(1)
        c.line(15 * mm, page_h - 60 * mm, page_w - 15 * mm, page_h - 60 * mm)

        # blocks
        c.setFont("Helvetica-Bold", 12)
        c.drawString(18 * mm, page_h - 70 * mm, "From")
        c.setFont("Helvetica", 12)
        c.drawString(35 * mm, page_h - 70 * mm, "The Stewards")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(18 * mm, page_h - 78 * mm, "To")
        c.setFont("Helvetica", 12)
        c.drawString(35 * mm, page_h - 78 * mm, "All Teams, All Officials")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(page_w - 75 * mm, page_h - 70 * mm, "Document")
        c.setFont("Helvetica", 12)
        c.drawString(page_w - 50 * mm, page_h - 70 * mm, f"DOC-{datetime.now():%H%M}")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(page_w - 75 * mm, page_h - 78 * mm, "Date")
        c.setFont("Helvetica", 12)
        c.drawString(page_w - 50 * mm, page_h - 78 * mm, datetime.now().strftime("%d %B %Y"))

        c.setFont("Helvetica-Bold", 12)
        c.drawString(page_w - 75 * mm, page_h - 86 * mm, "Time")
        c.setFont("Helvetica", 12)
        c.drawString(page_w - 50 * mm, page_h - 86 * mm, datetime.now().strftime("%H:%M"))

        c.line(15 * mm, page_h - 92 * mm, page_w - 15 * mm, page_h - 92 * mm)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(18 * mm, page_h - 105 * mm, "Title")
        c.setFont("Helvetica", 12)
        c.drawString(35 * mm, page_h - 105 * mm, title)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(18 * mm, page_h - 113 * mm, "Description")
        c.setFont("Helvetica", 12)
        c.drawString(45 * mm, page_h - 113 * mm, f"{title} Report")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(18 * mm, page_h - 121 * mm, "Enclosed")
        c.setFont("Helvetica", 12)
        c.drawString(45 * mm, page_h - 121 * mm, filename)

        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(page_w - 15 * mm, page_h - 140 * mm, "The Stewards")

    def _find_best_lap_driver(self):
        """
        VB: bestLapDrv = drivers.FirstOrDefault(d.Number = raceMan.BestLapDriver)
        """
        best_num = getattr(self.race_man, "best_lap_driver", None)
        if best_num is None:
            return None
        for d in self.race_man.session_race_list.drivers:
            if d.number == best_num:
                return d
        return None
