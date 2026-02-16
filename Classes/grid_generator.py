from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import List, Optional

from Classes.grid_driver import GridDriver

# PDF (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, black, dimgray, white
from reportlab.pdfgen import canvas


class GridGenerator:
    """
    Porting VB GridGenerator -> Python.

    - NIENTE OpenFileDialog qui (UI verrà fatta in UI/)
    - load_drivers_from_json(path)
    - build_final_grid(base, final_top4)
    - apply_penalties_and_pit_lane(grid)
    - generate_pdf(grid, output_path, endurance_grid, logo_path=...)
    """

    # ===== PAGE CONFIG (A4) =====
    PAGE_W, PAGE_H = A4
    MARGIN = 50
    COLUMN_GAP = 20

    # ===== LAYOUT =====
    HEADER_H = 88
    GRID_TOP_GAP = 10
    ROW_H = 60
    PAIR_GAP = 12
    GRID_STAGGER_Y = 14
    GRID_STAGGER_X = 8

    # ===== THEME =====
    ACCENT = Color(0 / 255, 150 / 255, 255 / 255, 1)
    CARD_BG = Color(252 / 255, 252 / 255, 252 / 255, 1)
    CARD_BORDER = Color(215 / 255, 215 / 255, 215 / 255, 1)
    BADGE_BG = Color(245 / 255, 245 / 255, 245 / 255, 1)
    PENALTY_RED = Color(160 / 255, 0 / 255, 0 / 255, 1)

    # ----------------------------
    # JSON -> Driver list
    # ----------------------------
    @staticmethod
    def load_drivers_from_json(path: str | Path) -> List[GridDriver]:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))

        drivers: List[GridDriver] = []
        for d in data.get("drivers", []):
            drivers.append(
                GridDriver(
                    name=str(d.get("name", "")),
                    surname=str(d.get("surname", "")),
                    race_number=int(d.get("number", 0)),
                    team=str(d.get("team", "")),
                    position=int(d.get("position", 0)),
                    best_lap=str(d.get("bestLap", "")),
                )
            )

        return sorted(drivers, key=lambda x: x.position)

    # ----------------------------
    # FIA grid merge (2 sessions)
    # ----------------------------
    @staticmethod
    def build_final_grid(base_drivers: List[GridDriver], final_drivers: List[GridDriver]) -> List[GridDriver]:
        result: List[GridDriver] = []

        # Prime 4 dalla sessione finale
        for i in range(min(4, len(final_drivers))):
            d = final_drivers[i]
            d.position = i + 1
            result.append(d)

        # Tutti gli altri dalla sessione base
        for d in base_drivers:
            if not any(x.race_number == d.race_number for x in result):
                d.position = len(result) + 1
                result.append(d)

        return sorted(result, key=lambda x: x.position)

    # ----------------------------
    # Apply grid penalties
    # ----------------------------
    @staticmethod
    def apply_penalties_and_pit_lane(grid: List[GridDriver]) -> List[GridDriver]:
        ordered = sorted(grid, key=lambda d: d.position)
        grid_count = len(ordered)

        # desired + pit
        for d in ordered:
            desired = d.position + max(0, d.grid_drop)
            d.desired_pos_after_penalty = desired
            d.pit_lane_start = desired > grid_count

        # GRID only
        grid_only = sorted(
            [d for d in ordered if not d.pit_lane_start],
            key=lambda d: (d.desired_pos_after_penalty, d.position),
        )
        for i, d in enumerate(grid_only):
            d.position = i + 1

        # PIT only
        pit_only = sorted(
            [d for d in ordered if d.pit_lane_start],
            key=lambda d: (d.desired_pos_after_penalty, d.position),
        )

        return grid_only + pit_only

    # ----------------------------
    # PDF generation (3 pages)
    # ----------------------------
    def generate_pdf(
        self,
        grid: List[GridDriver],
        output_path: str | Path,
        endurance_grid: List[GridDriver],
        logo_path: Optional[str | Path] = None,
    ) -> None:
        output_path = Path(output_path)
        c = canvas.Canvas(str(output_path), pagesize=A4)

        # Page 1: final grid
        self._render_grid_page(c, grid, "FINAL STARTING GRID", endurance=False, logo_path=logo_path)
        c.showPage()

        # Page 2: sprint grid (inversa)
        sprint_grid = [
            replace(d, position=i + 1)
            for i, d in enumerate(sorted(grid, key=lambda x: x.position, reverse=True))
        ]
        self._render_grid_page(c, sprint_grid, "SPRINT STARTING GRID", endurance=False, logo_path=logo_path)
        c.showPage()

        # Page 3: endurance grid
        self._render_grid_page(c, endurance_grid, "ENDURANCE FINAL GRID", endurance=True, logo_path=logo_path)
        c.save()

    # ----------------------------
    # Rendering helpers
    # ----------------------------
    def _render_grid_page(
        self,
        c: canvas.Canvas,
        grid: List[GridDriver],
        header_title: str,
        endurance: bool,
        logo_path: Optional[str | Path],
    ) -> None:
        y = self.MARGIN
        self._draw_header(c, y, header_title, logo_path)
        y += self.HEADER_H + self.GRID_TOP_GAP
        self._draw_grid(c, y, grid, endurance)
        self._draw_footer(c, 40)


    def _draw_header(self, c: canvas.Canvas, y: float, header_title: str, logo_path: Optional[str | Path]) -> None:
        header_font = "Helvetica"
        title_font = "Helvetica-Bold"

        # blocchi top
        left_x = self.MARGIN
        right_x = self.PAGE_W - self.MARGIN

        c.setFillColor(black)
        c.setFont(header_font, 9)
        c.drawString(left_x, self.PAGE_H - y - 14, "The Stewards")
        c.drawString(left_x, self.PAGE_H - y - 28, f"Date {self._now_date_long()}")

        c.drawRightString(right_x, self.PAGE_H - y - 14, "Document")
        c.drawRightString(right_x, self.PAGE_H - y - 28, f"Time {self._now_time()}")

        # logo
        if logo_path:
            try:
                lp = Path(logo_path)
                if lp.exists():
                    # pos simile al VB
                    c.drawImage(str(lp), self.MARGIN, self.PAGE_H - (y + 38 + 40), width=80, height=40, mask="auto")
            except Exception:
                pass

        # titoli centrali
        center_y = self.PAGE_H - (y + 40)
        c.setFont(title_font, 16)
        c.drawCentredString(self.PAGE_W / 2, center_y, header_title)

        c.setFont(title_font, 11)
        c.drawCentredString(self.PAGE_W / 2, center_y - 20, self._now_date_short())

    def _draw_grid(self, c: canvas.Canvas, start_y_from_top: float, grid: List[GridDriver], endurance: bool) -> None:
        # in reportlab l’origine Y è in basso -> convertiamo con PAGE_H
        col_w = (self.PAGE_W - self.MARGIN * 2 - self.COLUMN_GAP) / 2
        left_x = self.MARGIN
        right_x = self.MARGIN + col_w + self.COLUMN_GAP

        for i, d in enumerate(grid):
            is_right = (i % 2 == 1)
            pair_index = i // 2

            base_row_y_top = start_y_from_top + pair_index * (self.ROW_H + self.PAIR_GAP)
            row_y_top = base_row_y_top + (self.GRID_STAGGER_Y if is_right else 0)
            col_x = (right_x + self.GRID_STAGGER_X) if is_right else left_x

            # convert top-y to bottom-y for reportlab
            y_bottom = self.PAGE_H - (row_y_top + self.ROW_H)
            self._draw_driver_cell(c, d, col_x, y_bottom, col_w, endurance)

    def _draw_driver_cell(self, c: canvas.Canvas, d: GridDriver, x: float, y: float, w: float, endurance: bool) -> None:
        pad = 10
        radius = 12
        accent_w = 22

        # card rect
        c.setStrokeColor(self.CARD_BORDER)
        c.setFillColor(self.CARD_BG)
        c.roundRect(x + 1, y + 1, w - 2, self.ROW_H - 2, radius, stroke=1, fill=1)

        # accent bar (sinistra)
        c.setFillColor(self.ACCENT)
        c.setStrokeColor(self.ACCENT)
        c.roundRect(x + 1, y + 1, accent_w, self.ROW_H - 2, 10, stroke=0, fill=1)

        # label pos verticale (approssimazione: testo ruotato)
        label = "PIT LANE" if d.pit_lane_start else f"P{d.position}"
        c.saveState()
        c.translate(x + 1 + accent_w / 2, y + 1 + (self.ROW_H - 2) / 2)
        c.rotate(90)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(0, -4, label)
        c.restoreState()

        text_left = x + 1 + accent_w + pad
        name_y = y + self.ROW_H - 26
        team_y = y + self.ROW_H - 46

        # Nome / titolo
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 12)
        if not endurance:
            full_name = d.name_surname()
        else:
            full_name = d.team
        c.drawString(text_left, name_y, full_name)

        # Riga 2: team + tempo
        c.setFillColor(dimgray)
        c.setFont("Helvetica", 9)
        team_text = (f"{d.team} - " if not endurance else "Qualification Time: ")
        c.drawString(text_left, team_y, team_text)

        # tempo in bold
        team_w = c.stringWidth(team_text, "Helvetica", 9)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(text_left + team_w, team_y, d.best_lap)

        # penalità
        if d.grid_drop > 0 and not d.pit_lane_start:
            pen_text = f"  +{d.grid_drop} pos. Grid Pen."
            time_w = c.stringWidth(d.best_lap, "Helvetica-Bold", 9)
            c.setFillColor(self.PENALTY_RED)
            c.setFont("Helvetica-Bold", 7)
            c.drawString(text_left + team_w + time_w, team_y, pen_text)

    def _draw_footer(self, c: canvas.Canvas, y_from_bottom: float = 40) -> None:
        """
        Footer: y_from_bottom = distanza dal fondo pagina (in punti).
        """
        footer_text = (
            "Francesco Troianiello    "
            "Luca Pascali    "
            "Lorenzo Pompignoli    "
            "Francesco Paolo di Salvo"
        )

        # linea sopra footer
        c.setStrokeColor(self.CARD_BORDER)
        c.setLineWidth(0.8)
        c.line(self.MARGIN, y_from_bottom + 22, self.PAGE_W - self.MARGIN, y_from_bottom + 22)

        # Nomi
        c.setFillColor(black)
        c.setFont("Helvetica", 9)
        c.drawCentredString(self.PAGE_W / 2, y_from_bottom + 8, footer_text)

        # The Stewards
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(self.PAGE_W / 2, y_from_bottom - 6, "The Stewards")



    # ---- time helpers ----
    @staticmethod
    def _now_date_short() -> str:
        from datetime import datetime
        return datetime.now().strftime("%d-%m-%Y")

    @staticmethod
    def _now_date_long() -> str:
        from datetime import datetime
        # stile simile al VB "dd MMMM yyyy"
        return datetime.now().strftime("%d %B %Y")

    @staticmethod
    def _now_time() -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M")
