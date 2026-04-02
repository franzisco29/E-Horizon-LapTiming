from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QDialog,
	QHBoxLayout,
	QPushButton,
	QTableWidgetItem,
	QWidget,
)

from Classes.driver import Driver
from Classes.race_list import RaceList
from Modules.log_utils import log
from UI.ResultPreviewWindow.penalty_add_dialog import PenaltyAddDialog
from UI.ResultPreviewWindow.result_preview_window_ui import build_result_preview_ui, ResultPreviewWindowRefs


@dataclass(slots=True)
class PenaltyEntry:
	seconds: int
	motivation: str


@dataclass(slots=True)
class _PreviewRow:
	driver: Driver
	penalties: List[PenaltyEntry] = field(default_factory=list)

	@property
	def total_seconds(self) -> int:
		return sum(max(0, int(p.seconds)) for p in self.penalties)

	def avg_lap_seconds(self, race_mode: bool) -> float:
		history = list(getattr(self.driver, "lap_history", []) or [])
		if race_mode and len(history) > 1:
			history = history[1:]
		if not history:
			return 0.0
		values = [max(0.0, float(l.total_seconds())) for l in history]
		values = [v for v in values if v > 0.0]
		if not values:
			return 0.0
		return sum(values) / len(values)

	def lap_equivalent(self, race_mode: bool) -> Optional[float]:
		avg = self.avg_lap_seconds(race_mode)
		if avg <= 0:
			return None
		return self.total_seconds / avg

	def lap_penalty_split(self, race_mode: bool) -> tuple[Optional[int], Optional[float], Optional[float]]:
		avg = self.avg_lap_seconds(race_mode)
		if avg <= 0:
			return None, None, None
		# Use the same precision shown in table (0.1s) so split is predictable for users.
		avg_shown = round(avg, 1)
		if avg_shown <= 0:
			return None, None, None
		laps = int(self.total_seconds // avg_shown)
		residual = float(self.total_seconds) - (laps * avg_shown)
		if residual < 0:
			residual = 0.0
		return laps, residual, avg_shown


def _fmt_mm_ss_mmm(td: timedelta) -> str:
	total_ms = int(max(0.0, td.total_seconds()) * 1000)
	minutes = total_ms // 60000
	seconds = (total_ms % 60000) // 1000
	millis = total_ms % 1000
	return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


def _fmt_seconds(value: float) -> str:
	if value <= 0:
		return "0"
	rounded = round(value)
	if abs(value - rounded) < 0.05:
		return str(int(rounded))
	return f"{value:.1f}"


class ResultPreviewWindow(QDialog):
	def __init__(self, race_man: Any, source_race_list: RaceList, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setWindowTitle("Preview risultati")
		self.resize(1280, 720)

		self.race_man = race_man
		self.source_race_list = source_race_list
		self._race_mode = bool(getattr(race_man, "race", False))

		root, refs = build_result_preview_ui(self)
		self.refs: ResultPreviewWindowRefs = refs

		main = QHBoxLayout(self)
		main.setContentsMargins(0, 0, 0, 0)
		main.addWidget(root)

		# Deep copy: isolamento totale dal modello live
		self._rows: List[_PreviewRow] = [
			_PreviewRow(driver=copy.deepcopy(d)) for d in list(getattr(source_race_list, "drivers", []) or [])
		]

		self.refs.buttons.accepted.connect(self.accept)
		self.refs.buttons.rejected.connect(self.reject)

		self._render_preview()

	def keyPressEvent(self, event) -> None:
		if event.key() in (Qt.Key_Return, Qt.Key_Enter):
			event.accept()
			return
		super().keyPressEvent(event)

	def penalty_map(self) -> Dict[int, int]:
		out: Dict[int, int] = {}
		for row in self._rows:
			sec = row.total_seconds
			if sec > 0:
				out[int(row.driver.number)] = sec
		return out

	def penalties_for_pdf(self) -> List[Dict[str, Any]]:
		out: List[Dict[str, Any]] = []
		for row in self._rows:
			laps, residual, avg = row.lap_penalty_split(self._race_mode)
			lap_str = "-"
			avg_str = "-"
			if laps is not None and residual is not None:
				lap_str = f"{laps}L + {_fmt_seconds(residual)}s"
			if avg is not None:
				avg_str = f"{_fmt_seconds(avg)}s"
			for p in row.penalties:
				out.append(
					{
						"driver_name": row.driver.name_surname(),
						"driver_number": int(row.driver.number),
						"race_number": int(getattr(row.driver, "race_number", 0) or 0),
						"seconds": int(p.seconds),
						"motivation": str(p.motivation),
						"avg_lap": avg_str,
						"lap_penalty": lap_str,
					}
				)
		return out

	def build_penalized_copy(self) -> RaceList:
		# Copia completa della RaceList con driver gia deep-copiati e penalizzati
		out = copy.deepcopy(self.source_race_list)
		by_number: Dict[int, _PreviewRow] = {int(r.driver.number): r for r in self._rows}

		for d in out.drivers:
			row = by_number.get(int(d.number))
			if not row:
				continue
			sec = row.total_seconds
			if sec <= 0:
				continue

			if self._race_mode:
				laps_pen, residual_sec, _avg = row.lap_penalty_split(self._race_mode)
				if laps_pen is not None and laps_pen > 0:
					d.laps = max(0, int(getattr(d, "laps", 0)) - int(laps_pen))

				# In race mode, convert total penalty into: integer laps + residual seconds.
				extra = timedelta(seconds=(residual_sec if residual_sec is not None else 0.0))
				d.sort_time = d.sort_time + extra
				if getattr(d, "time_on_track", timedelta(0)).total_seconds() > 0:
					d.time_on_track = d.time_on_track + extra
				else:
					d.time_on_track = d.sort_time - d.start_time
			else:
				extra = timedelta(seconds=sec)
				d.fast_lap = d.fast_lap + extra

		# Ricalcolo ordine/posizioni/delta sulla copia, senza toccare il modello live.
		rm = self.race_man
		original_list = getattr(rm, "session_race_list", None)
		try:
			rm.session_race_list = out
			if hasattr(rm, "_calculate_delta"):
				rm._calculate_delta()
			else:
				self._fallback_reorder(out)
		except Exception as e:
			log(f"[RISULTATI] Ricalcolo delta fallback: {e}", level="WARN")
			self._fallback_reorder(out)
		finally:
			rm.session_race_list = original_list

		return out

	def _fallback_reorder(self, race_list: RaceList) -> None:
		if self._race_mode:
			sectors_on = bool(getattr(getattr(self.race_man, "session", None), "sectors_on", False))

			def key(d: Driver):
				sec_rank = -d.actual_sector if sectors_on else 0
				return (-d.laps, sec_rank, d.sort_time)

			race_list.drivers.sort(key=key)
			leader = race_list.drivers[0] if race_list.drivers else None
			for i, d in enumerate(race_list.drivers):
				d.position = i + 1
				if i == 0 or leader is None:
					continue
				prev = race_list.drivers[i - 1]
				d.delta = d.sort_time - prev.sort_time
				d.leader_delta = d.sort_time - leader.sort_time
				d.laps_behind[1] = max(0, prev.laps - d.laps)
				d.laps_behind[0] = max(0, leader.laps - d.laps)
		else:
			race_list.drivers.sort(
				key=lambda d: (1, timedelta.max) if d.fast_lap.total_seconds() <= 0 else (0, d.fast_lap)
			)
			leader = race_list.drivers[0] if race_list.drivers else None
			for i, d in enumerate(race_list.drivers):
				d.position = i + 1
				if i == 0 or leader is None:
					continue
				prev = race_list.drivers[i - 1]
				d.delta = d.fast_lap - prev.fast_lap
				d.leader_delta = d.fast_lap - leader.fast_lap

	def _render_preview(self) -> None:
		# Preview calcolata su una copia penalizzata e ordinata
		preview = self.build_penalized_copy()
		row_by_number = {int(r.driver.number): r for r in self._rows}

		table = self.refs.table
		table.setRowCount(len(preview.drivers))

		for row_idx, d in enumerate(preview.drivers):
			src = row_by_number.get(int(d.number))
			total_pen = src.total_seconds if src else 0
			laps, residual, avg_lap = src.lap_penalty_split(self._race_mode) if src else (None, None, None)

			base_time = src.driver.time_on_track if (self._race_mode and src) else d.time_on_track
			if not self._race_mode:
				base_time = src.driver.fast_lap if src else d.fast_lap
			corrected_time = d.time_on_track if self._race_mode else d.fast_lap

			best = False
			if self._race_mode:
				best_num = getattr(self.race_man, "best_lap_driver", None)
				best = best_num is not None and int(best_num) == int(d.number)
			points = self.race_man.get_points(d.position, best)

			self._set_item(row_idx, 0, str(d.position), align=Qt.AlignCenter)
			self._set_item(row_idx, 1, d.name_surname())
			self._set_item(row_idx, 2, str(getattr(d, "team", "")))
			self._set_item(row_idx, 3, str(getattr(d, "laps", 0)), align=Qt.AlignCenter)
			self._set_item(row_idx, 4, _fmt_mm_ss_mmm(base_time), align=Qt.AlignCenter)

			ptxt = "-"
			tooltip = ""
			if src and src.penalties:
				ptxt = f"+ {total_pen} s"
				tooltip = "\n".join([f"+{p.seconds}s - {p.motivation}" for p in src.penalties])
			pen_item = self._set_item(row_idx, 5, ptxt, align=Qt.AlignCenter)
			if ptxt != "-":
				pen_item.setToolTip("Penalita totale applicata in secondi")
			if tooltip:
				pen_item.setToolTip(tooltip)

			avg_txt = "-" if avg_lap is None else f"{_fmt_seconds(avg_lap)}s"
			self._set_item(row_idx, 6, avg_txt, align=Qt.AlignCenter)

			lap_pen_txt = "-"
			if laps is not None and residual is not None:
				lap_pen_txt = f"{laps} giri + {_fmt_seconds(residual)} s"
			self._set_item(row_idx, 7, lap_pen_txt, align=Qt.AlignCenter)

			self._set_item(row_idx, 8, _fmt_mm_ss_mmm(corrected_time), align=Qt.AlignCenter)
			self._set_item(row_idx, 9, str(d.get_status_string()), align=Qt.AlignCenter)
			self._set_item(row_idx, 10, str(points), align=Qt.AlignCenter)

			table.setCellWidget(row_idx, 11, self._build_actions_widget(int(d.number)))

		table.resizeRowsToContents()

	def _build_actions_widget(self, driver_number: int) -> QWidget:
		w = QWidget(self.refs.table)
		lay = QHBoxLayout(w)
		lay.setContentsMargins(0, 0, 0, 0)
		lay.setSpacing(4)

		add_btn = QPushButton("+", w)
		add_btn.setFixedWidth(28)
		add_btn.clicked.connect(lambda _checked=False, dn=driver_number: self._on_add_penalty(dn))

		rem_btn = QPushButton("-", w)
		rem_btn.setFixedWidth(28)
		rem_btn.clicked.connect(lambda _checked=False, dn=driver_number: self._on_remove_penalty(dn))

		lay.addWidget(add_btn)
		lay.addWidget(rem_btn)
		lay.addStretch(1)
		return w

	def _find_row_by_number(self, driver_number: int) -> Optional[_PreviewRow]:
		for row in self._rows:
			if int(row.driver.number) == int(driver_number):
				return row
		return None

	def _on_add_penalty(self, driver_number: int) -> None:
		row = self._find_row_by_number(driver_number)
		if row is None:
			return

		dlg = PenaltyAddDialog(driver_name=row.driver.name_surname(), parent=self)
		if dlg.exec() != QDialog.Accepted:
			return

		row.penalties.append(PenaltyEntry(seconds=dlg.seconds, motivation=dlg.motivation))
		self._render_preview()

	def _on_remove_penalty(self, driver_number: int) -> None:
		row = self._find_row_by_number(driver_number)
		if row is None:
			return
		if row.penalties:
			row.penalties.pop()
			self._render_preview()

	def _set_item(self, row: int, col: int, text: str, align: Optional[Qt.AlignmentFlag] = None) -> QTableWidgetItem:
		item = QTableWidgetItem(text)
		if align is not None:
			item.setTextAlignment(int(align))
		self.refs.table.setItem(row, col, item)
		return item

