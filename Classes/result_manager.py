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
def fmt_mm_ss_mmm(td: timedelta) -> str:
    if td is None:
        return ""
    total_ms = int(td.total_seconds() * 1000)
    if total_ms < 0:
        total_ms = 0
    minutes = total_ms // 60000
    seconds = (total_ms % 60000) // 1000
    millis = total_ms % 1000
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


def fmt_m_ss_mmm(td: timedelta) -> str:
    # per lap history usa m:ss.fff
    if td is None:
        return ""
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

    # ----------------------------
    # Public API
    # ----------------------------
    def generate_result_pdf(self, root_path: str) -> Path:
        """
        VB: GenerateResultPDF()
        Crea PDF in <root_path>/Results/Results <session> <date>.pdf
        + salva RAW json.
        """
        if not self.event_name:
            self.event_name = "E-HORIZON CHAMPIONSHIP"

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
                # TIME = race_time in VB (mm:ss.fff)
                c.drawString(x[4], y, fmt_mm_ss_mmm(drv.race_time))
            else:
                # in qualy: TIME column swapped with FASTEST
                c.drawString(x[7], y, fmt_mm_ss_mmm(drv.fast_lap))

            c.drawString(x[5], y, drv.print_delta(False))
            c.drawString(x[6], y, drv.print_delta(True))

            if self.race_man.race:
                c.drawString(x[7], y, fmt_mm_ss_mmm(drv.fast_lap))
            else:
                c.drawString(x[4], y, fmt_mm_ss_mmm(drv.race_time))

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

        # Pit stops section
        if self.race_man.race:
            if y < 70 * mm:
                c.showPage()
                y = page_h - 20 * mm

            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(x[0] + table_w / 2, y, "PIT STOPS")
            y -= 10 * mm

            pit_headers = ["POS", "DRIVER", "TEAM", "PIT TIME"]
            pit_w = [10 * mm, 48 * mm, 34 * mm, 20 * mm]
            pit_x = self._centered_x_positions(page_w, pit_w)

            c.setFont("Helvetica", 8.5)
            for i, h in enumerate(pit_headers):
                c.drawString(pit_x[i], y, h)
            y -= 6 * mm

            # order pit times
            for d in drivers:
                d.order_pit_times()

            drivers_by_pit = sorted(drivers, key=lambda d: d.pit_times[0] if d.pit_times else timedelta.max)

            posi = 1
            for drv in drivers_by_pit:
                best_pit = drv.pit_times[0] if drv.pit_times else timedelta.max
                if best_pit == timedelta.max:
                    continue

                if y < 25 * mm:
                    c.showPage()
                    y = page_h - 20 * mm

                c.drawString(pit_x[0], y, str(posi))

                if getattr(self.race_man, "endurance", False):
                    roadsters = getattr(self.race_man.session_race_list, "roadsters", None) or []
                    idx = next((r for r in roadsters if drv.number in r.numbers), None)
                    name_txt = idx.to_result() if idx else drv.name_surname()
                else:
                    name_txt = drv.name_surname()

                c.drawString(pit_x[1], y, name_txt)
                c.drawString(pit_x[2], y, self._shorten_team_name(drv.team))
                c.drawString(pit_x[3], y, fmt_mm_ss_mmm(best_pit))

                y -= 6 * mm
                posi += 1

        # Footer
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        c.setFont("Helvetica", 7)
        c.drawString(15 * mm, 12 * mm, "Approved by General Director E-Horizon Francesco Troianiello")
        c.drawRightString(page_w - 15 * mm, 12 * mm, date_str)

        c.save()

        # Save RAW
        self.save_raw_data(root_path=str(Path(root_path)), pdf_filename=str(filename))

        return filename

    def generate_lap_history_pdf(self, root_path: str) -> Path:
        """
        VB: GenerateLapHistoryPDF()
        """
        drivers = list(self.race_man.session_race_list.drivers)
        max_pilots_per_page = 6

        doc_path = Path(root_path) / f"LapHistory_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        c = canvas.Canvas(str(doc_path), pagesize=A4)
        page_w, page_h = A4

        all_drivers = sorted(drivers, key=lambda d: d.number)
        max_laps = max((len(d.lap_history) for d in all_drivers), default=0)

        pages = (len(all_drivers) + max_pilots_per_page - 1) // max_pilots_per_page

        for page_index in range(pages):
            y = page_h - 20 * mm
            y = self._draw_logo_centered(c, page_w, y, max_w=35 * mm, max_h=35 * mm)

            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(page_w / 2, page_h - 55 * mm, "Lap History Report")

            c.setFont("Helvetica-Bold", 11)
            c.drawString(15 * mm, page_h - 70 * mm, f"Sessione: {self._get_session_name()}")
            c.drawRightString(page_w - 15 * mm, page_h - 70 * mm, f"Data: {datetime.now():%d/%m/%Y %H:%M}")

            margin_left = 15 * mm
            margin_top = page_h - 90 * mm
            col_w = 22 * mm
            col_spacing = 3 * mm
            row_h = 7 * mm

            drivers_this_page = all_drivers[page_index * max_pilots_per_page:(page_index + 1) * max_pilots_per_page]

            best_laps = []
            for d in drivers_this_page:
                best_laps.append(min(d.lap_history) if d.lap_history else timedelta.max)

            # Header row
            col_x = margin_left
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(col_x + col_w / 2, margin_top, "Lap")
            col_x += col_w + col_spacing

            for d in drivers_this_page:
                c.drawCentredString(col_x + col_w / 2, margin_top, f"Car N.{d.race_number:02d}")
                col_x += col_w + col_spacing

            # Rows
            y_row = margin_top - row_h
            for lap_index in range(max_laps):
                if y_row < 20 * mm:
                    break

                col_x = margin_left
                c.setFont("Helvetica", 9.5)
                c.drawCentredString(col_x + col_w / 2, y_row, str(lap_index + 1))
                col_x += col_w + col_spacing

                for i, d in enumerate(drivers_this_page):
                    lap_str = ""
                    font_name = "Helvetica"
                    font_size = 9.5

                    if len(d.lap_history) > lap_index:
                        t = d.lap_history[lap_index]
                        lap_str = fmt_m_ss_mmm(t)
                        if t == best_laps[i]:
                            font_name = "Helvetica-Bold"

                    c.setFont(font_name, font_size)
                    c.drawCentredString(col_x + col_w / 2, y_row, lap_str)
                    col_x += col_w + col_spacing

                y_row -= row_h

            # Footer
            c.setFont("Helvetica", 9)
            c.drawString(15 * mm, 12 * mm, "Approvato dal Direttore Generale E-Horizon Francesco Troianiello")
            c.drawRightString(page_w - 15 * mm, 12 * mm, datetime.now().strftime("%d/%m/%Y %H:%M"))

            c.showPage()

        c.save()
        return doc_path

    def save_raw_data(self, root_path: str, pdf_filename: str) -> Path:
        """
        VB: SaveRawData(raceManager, filename)
        filename -> RAW json con stesso nome base.
        """
        raw_dir = Path(root_path) / "RAW"
        raw_dir.mkdir(parents=True, exist_ok=True)

        # base filename (senza estensione)
        base = Path(pdf_filename).stem.replace("Results", "RAW")
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
            driver_data["team"] = d.team
            driver_data["laps"] = d.laps
            driver_data["history"] = [fmt_mm_ss_mmm(ts) for ts in d.lap_history]
            driver_data["bestLap"] = fmt_mm_ss_mmm(d.fast_lap)
            driver_data["position"] = d.position
            driver_data["totalTime"] = fmt_mm_ss_mmm(d.time_on_track)
            driver_data["interval"] = d.print_delta(True)
            driver_data["leader"] = d.print_delta(False)
            driver_data["entryPitTimes"] = [fmt_mm_ss_mmm(ts) for ts in d.pit_in_times]
            driver_data["pitTimes"] = [fmt_mm_ss_mmm(ts) for ts in d.pit_times]

            best = bool(rm.race and best_lap_drv and best_lap_drv.number == d.number)
            driver_data["points"] = rm.get_points(d.position, best)

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
