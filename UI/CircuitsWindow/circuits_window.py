from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout

from Modules.config_manager import Settings
from Modules.db import Database, db_path_from_root, init_db
from Modules.repositories.circuits_repo import CircuitRow, CircuitsRepo
from UI.CircuitsWindow.circuits_window_ui import CircuitsWindowUI


class CircuitsWindow(QDialog):
    def __init__(self, parent, settings: Settings):
        super().__init__(parent)
        self.settings = settings

        db_path = db_path_from_root(settings.root_path, filename="ehorizon.db")
        self.db = Database(db_path)
        init_db(self.db)

        self.repo = CircuitsRepo(self.db)

        self.ui = CircuitsWindowUI(self)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.addWidget(self.ui)

        self.all_circuits: List[CircuitRow] = []
        self.filtered: List[CircuitRow] = []
        self.selected_circuit_id: Optional[int] = None
        self._row_buttons: List[QPushButton] = []
        self._row_ids: List[int] = []

        r = self.ui.refs
        r.reset_btn.clicked.connect(self.reset_form)
        r.save_btn.clicked.connect(self.create_or_update)
        r.delete_btn.clicked.connect(self.delete_selected)
        r.search_entry.textChanged.connect(lambda _t: self.apply_filter())

        r.scroll_area.viewport().installEventFilter(self)

        self.refresh()

    def eventFilter(self, obj, event):
        if obj is self.ui.refs.scroll_area.viewport() and event.type() == QEvent.MouseButtonPress:
            try:
                pos = event.position().toPoint()
            except Exception:
                pos = event.pos()
            w = obj.childAt(pos)
            if not (isinstance(w, QPushButton) and w.objectName() == "CircuitRow"):
                self.deselect()
        return super().eventFilter(obj, event)

    def set_status(self, text: str) -> None:
        self.ui.refs.status_label.setText(text)

    def _parse_float_field(self, label: str, value: str) -> Optional[float]:
        text = (value or "").strip().replace(",", ".")
        try:
            out = float(text)
        except Exception:
            QMessageBox.warning(self, "Invalid value", f"{label} must be a number.")
            return None
        if out <= 0:
            QMessageBox.warning(self, "Invalid value", f"{label} must be > 0.")
            return None
        return out

    def _get_selected_row(self) -> Optional[CircuitRow]:
        if self.selected_circuit_id is None:
            return None
        return next((c for c in self.all_circuits if c.circuit_id == self.selected_circuit_id), None)

    def reset_form(self) -> None:
        r = self.ui.refs
        r.name_entry.clear()
        r.location_entry.clear()
        r.track_len_entry.clear()
        r.s1_entry.clear()
        r.s2_entry.clear()
        r.s3_entry.clear()
        r.notes_entry.clear()

        self.selected_circuit_id = None
        self.highlight_selected()
        self.set_status("Ready (new circuit).")

    def fill_form(self, c: CircuitRow) -> None:
        r = self.ui.refs
        r.name_entry.setText(c.name)
        r.location_entry.setText(c.location)
        r.track_len_entry.setText(str(c.track_length_m))
        r.s1_entry.setText(str(c.sector1_m))
        r.s2_entry.setText(str(c.sector2_m))
        r.s3_entry.setText(str(c.sector3_m))
        r.notes_entry.setPlainText(c.notes)

    def parse_form(self) -> Optional[CircuitRow]:
        r = self.ui.refs

        name = r.name_entry.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing fields", "Circuit name is required.")
            return None

        location = r.location_entry.text().strip()

        track_len = self._parse_float_field("Track Length", r.track_len_entry.text())
        if track_len is None:
            return None

        s1 = self._parse_float_field("Sector 1", r.s1_entry.text())
        if s1 is None:
            return None

        s2 = self._parse_float_field("Sector 2", r.s2_entry.text())
        if s2 is None:
            return None

        s3 = self._parse_float_field("Sector 3", r.s3_entry.text())
        if s3 is None:
            return None

        if self.repo.conflicts(name=name, exclude_id=self.selected_circuit_id):
            QMessageBox.warning(self, "Duplicate", "Circuit name already used.")
            return None

        sectors_sum = s1 + s2 + s3
        delta_ratio = abs(sectors_sum - track_len) / track_len if track_len > 0 else 0.0
        if delta_ratio > 0.10:
            ans = QMessageBox.question(
                self,
                "Confirm track lengths",
                "S1+S2+S3 differs from track length by more than 10%. Save anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return None

        return CircuitRow(
            circuit_id=self.selected_circuit_id or 0,
            name=name,
            location=location,
            track_length_m=track_len,
            sector1_m=s1,
            sector2_m=s2,
            sector3_m=s3,
            notes=r.notes_entry.toPlainText().strip(),
        )

    def refresh(self) -> None:
        self.all_circuits = self.repo.get_all()

        if self.selected_circuit_id is not None:
            if not any(c.circuit_id == self.selected_circuit_id for c in self.all_circuits):
                self.selected_circuit_id = None

        self.apply_filter()
        self.set_status(f"Loaded {len(self.all_circuits)} circuits.")

    def apply_filter(self) -> None:
        q = self.ui.refs.search_entry.text().strip().lower()
        base = self.all_circuits

        if q:
            def match(c: CircuitRow) -> bool:
                return (
                    q in c.name.lower()
                    or q in c.location.lower()
                    or q in str(c.track_length_m)
                    or q in str(c.circuit_id)
                )
            base = [c for c in base if match(c)]

        self.filtered = list(base)
        self.render_list()
        self.highlight_selected()

        if self.selected_circuit_id is not None:
            visible = next((c for c in self.filtered if c.circuit_id == self.selected_circuit_id), None)
            if visible is not None:
                self.fill_form(visible)

        if not self.filtered:
            self.set_status("No circuits found.")

    def _clear_list(self) -> None:
        layout = self.ui.refs.scroll_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._row_buttons.clear()
        self._row_ids.clear()

    def render_list(self) -> None:
        self._clear_list()
        layout = self.ui.refs.scroll_layout

        if not self.filtered:
            empty = QLabel("No circuits found.")
            empty.setStyleSheet("color:#7F8AA1; font-size:12px;")
            layout.addWidget(empty)
            layout.addStretch(1)
            return

        for c in self.filtered:
            btn = QPushButton(c.display())
            btn.setObjectName("CircuitRow")
            btn.setProperty("selected", False)
            btn.setCursor(Qt.PointingHandCursor)

            cid = c.circuit_id
            btn.clicked.connect(lambda _checked=False, x=cid: self.select_circuit(x))

            layout.addWidget(btn)
            self._row_buttons.append(btn)
            self._row_ids.append(cid)

        layout.addStretch(1)

    def highlight_selected(self) -> None:
        for btn, cid in zip(self._row_buttons, self._row_ids):
            btn.setProperty("selected", cid == self.selected_circuit_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def select_circuit(self, circuit_id: int) -> None:
        c = next((x for x in self.filtered if x.circuit_id == circuit_id), None)
        if c is None:
            c = next((x for x in self.all_circuits if x.circuit_id == circuit_id), None)
        if c is None:
            return

        self.selected_circuit_id = c.circuit_id
        self.fill_form(c)
        self.highlight_selected()
        self.set_status(f"Selected: {c.display()}")

    def deselect(self) -> None:
        self.selected_circuit_id = None
        self.reset_form()
        self.highlight_selected()

    def create_or_update(self) -> None:
        row = self.parse_form()
        if not row:
            return

        try:
            new_id = self.repo.upsert(row)
        except Exception as e:
            QMessageBox.critical(self, "Database error", f"Unable to save circuit:\n{e}")
            return

        self.set_status(f"Saved circuit #{new_id}.")
        self.refresh()
        self.reset_form()

    def delete_selected(self) -> None:
        if self.selected_circuit_id is None:
            QMessageBox.information(self, "Delete", "Select a circuit first.")
            return

        row = self._get_selected_row()
        if row is None:
            self.selected_circuit_id = None
            self.refresh()
            return

        resp = QMessageBox.question(
            self,
            "Delete circuit",
            f"Delete circuit:\n\n{row.display()}\n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        try:
            self.repo.delete_by_id(row.circuit_id)
        except Exception as e:
            QMessageBox.critical(self, "Database error", f"Unable to delete circuit:\n{e}")
            return

        self.selected_circuit_id = None
        self.set_status(f"Deleted circuit #{row.circuit_id}.")
        self.refresh()
        self.reset_form()
