from __future__ import annotations

from typing import List, Dict, Optional

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QPushButton, QLabel

from Modules.config_manager import Settings
from Modules.db import Database, db_path_from_root, init_db
from Modules.repositories.drivers_repo import DriversRepo, DriverRow
from Modules.repositories.roadsters_repo import RoadstersRepo, RoadsterRow


from UI.RoadsterWindow.roadster_window_ui import RoadsterWindowUI


class RoadsterWindow(QDialog):
    def __init__(self, parent, settings: Settings):
        super().__init__(parent)
        self.settings = settings

        db_path = db_path_from_root(settings.root_path, filename="ehorizon.db")
        self.db = Database(db_path)
        init_db(self.db)

        self.drivers_repo = DriversRepo(self.db)
        self.roadsters_repo = RoadstersRepo(self.db)

        self.ui = RoadsterWindowUI(self)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.addWidget(self.ui)

        # state
        self.all_drivers: List[DriverRow] = []
        self.drivers_by_id: Dict[int, DriverRow] = {}
        self.teams: List[str] = []

        self.all_roadsters: List[RoadsterRow] = []
        self.filtered_roadsters: List[RoadsterRow] = []
        self.selected_index: int = -1
        self._row_buttons: List[QPushButton] = []

        # bindings
        r = self.ui.refs
        r.reset_btn.clicked.connect(self.reset_form)
        r.save_btn.clicked.connect(self.create_or_update)
        r.delete_btn.clicked.connect(self.delete_selected)
        r.team_combo.currentIndexChanged.connect(lambda _i: self._sync_driver_lists())
        r.search_team_combo.currentIndexChanged.connect(lambda _i: self.apply_filter_and_render())

        # deselect on empty click
        r.scroll_area.viewport().installEventFilter(self)

        self.reload_all()

    def eventFilter(self, obj, event):
        if obj is self.ui.refs.scroll_area.viewport() and event.type() == QEvent.MouseButtonPress:
            w = obj.childAt(event.position().toPoint())
            if not isinstance(w, QPushButton) or w.objectName() != "RoadsterRow":
                self.deselect()
        return super().eventFilter(obj, event)

    def set_status(self, text: str) -> None:
        self.ui.refs.status_label.setText(text)

    # ---------- load ----------
    def reload_all(self) -> None:
        self.all_drivers = self.drivers_repo.get_all()
        self.drivers_by_id = {d.driver_id: d for d in self.all_drivers}

        self.teams = ["All"] + sorted({d.team for d in self.all_drivers if d.team})

        r = self.ui.refs
        # team combo (form)
        r.team_combo.blockSignals(True)
        r.team_combo.clear()
        r.team_combo.addItems(self.teams)
        r.team_combo.setCurrentIndex(0)
        r.team_combo.blockSignals(False)

        # team combo (filter list)
        r.search_team_combo.blockSignals(True)
        r.search_team_combo.clear()
        r.search_team_combo.addItems(self.teams)
        r.search_team_combo.setCurrentIndex(0)
        r.search_team_combo.blockSignals(False)

        self._sync_driver_lists()
        self.refresh_roadsters()

    def refresh_roadsters(self) -> None:
        self.all_roadsters = self.roadsters_repo.list_all()
        self.apply_filter_and_render()
        self.set_status(f"Loaded {len(self.all_roadsters)} roadsters.")

    def _sync_driver_lists(self) -> None:
        r = self.ui.refs
        team = r.team_combo.currentText()

        if team == "All":
            eligible = self.all_drivers
        else:
            eligible = [d for d in self.all_drivers if d.team == team]

        r.d1_combo.blockSignals(True)
        r.d2_combo.blockSignals(True)
        r.d1_combo.clear()
        r.d2_combo.clear()

        for d in eligible:
            label = d.display()  # "Name Surname | Team | # | Tras"
            r.d1_combo.addItem(label, userData=d.driver_id)
            r.d2_combo.addItem(label, userData=d.driver_id)

        if r.d1_combo.count() > 0:
            r.d1_combo.setCurrentIndex(0)
        if r.d2_combo.count() > 1:
            r.d2_combo.setCurrentIndex(1)
        elif r.d2_combo.count() > 0:
            r.d2_combo.setCurrentIndex(0)

        r.d1_combo.blockSignals(False)
        r.d2_combo.blockSignals(False)

    # ---------- selection ----------
    def deselect(self) -> None:
        self.selected_index = -1
        self.highlight_selected()
        self.set_status("Ready (no selection).")

    def reset_form(self) -> None:
        self.selected_index = -1
        self.ui.refs.team_combo.setCurrentIndex(0)
        self._sync_driver_lists()
        self.highlight_selected()
        self.set_status("Ready (new roadster).")

    def select_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.filtered_roadsters):
            return
        self.selected_index = idx
        rr = self.filtered_roadsters[idx]

        # set team (best-effort)
        team = rr.team if rr.team in self.teams else "All"
        self.ui.refs.team_combo.setCurrentText(team)  # triggers sync list

        # set driver combos by id
        self._set_combo_by_driver_id(self.ui.refs.d1_combo, rr.driver1_id)
        self._set_combo_by_driver_id(self.ui.refs.d2_combo, rr.driver2_id)

        self.highlight_selected()
        self.set_status(f"Selected roadster #{rr.roadster_id}.")

    def _set_combo_by_driver_id(self, combo, driver_id: int) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == driver_id:
                combo.setCurrentIndex(i)
                return

    # ---------- list render ----------
    def apply_filter_and_render(self) -> None:
        team = self.ui.refs.search_team_combo.currentText()
        if team == "All":
            self.filtered_roadsters = list(self.all_roadsters)
        else:
            self.filtered_roadsters = [r for r in self.all_roadsters if r.team == team]

        self.render_list()
        self.highlight_selected()

    def _clear_list(self) -> None:
        layout = self.ui.refs.scroll_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._row_buttons.clear()
        layout.addStretch(1)

    def render_list(self) -> None:
        self._clear_list()
        layout = self.ui.refs.scroll_layout

        if not self.filtered_roadsters:
            empty = QLabel("No roadsters found.")
            empty.setStyleSheet("color:#7F8AA1; font-size:10pt;")
            layout.addWidget(empty)
            return

        for i, rr in enumerate(self.filtered_roadsters):
            d1 = self.drivers_by_id.get(rr.driver1_id)
            d2 = self.drivers_by_id.get(rr.driver2_id)
            d1_label = d1.name + " "+ d1.surname if d1 else f"Driver #{rr.driver1_id}"
            d2_label = d2.name + " "+ d2.surname if d2 else f"Driver #{rr.driver2_id}"

            text = f"🏁  {d1_label}  +  {d2_label}   |   {rr.team}"
            btn = QPushButton(text)
            btn.setObjectName("RoadsterRow")
            btn.setProperty("selected", False)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, idx=i: self.select_index(idx))
            layout.addWidget(btn)
            self._row_buttons.append(btn)

    def highlight_selected(self) -> None:
        for i, btn in enumerate(self._row_buttons):
            btn.setProperty("selected", i == self.selected_index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    # ---------- CRUD ----------
    def create_or_update(self) -> None:
        r = self.ui.refs
        d1_id = r.d1_combo.currentData()
        d2_id = r.d2_combo.currentData()

        if d1_id is None or d2_id is None:
            QMessageBox.warning(self, "Roadster", "Select both drivers.")
            return
        if d1_id == d2_id:
            QMessageBox.warning(self, "Roadster", "Driver 1 and Driver 2 must be different.")
            return

        team = r.team_combo.currentText()
        if team == "All":
            d1 = self.drivers_by_id.get(int(d1_id))
            d2 = self.drivers_by_id.get(int(d2_id))
            if d1 and d2 and d1.team == d2.team:
                team = d1.team
            else:
                team = "Mixed"

        roadster_id = 0
        if 0 <= self.selected_index < len(self.filtered_roadsters):
            roadster_id = self.filtered_roadsters[self.selected_index].roadster_id

        try:
            new_id = self.roadsters_repo.upsert(roadster_id, team, int(d1_id), int(d2_id))
        except Exception as e:
            QMessageBox.critical(self, "Database error", f"Unable to save roadster:\n{e}")
            return

        self.set_status(f"Saved roadster #{new_id}.")
        self.refresh_roadsters()
        self.reset_form()

    def delete_selected(self) -> None:
        if not (0 <= self.selected_index < len(self.filtered_roadsters)):
            QMessageBox.information(self, "Delete", "Select a roadster first.")
            return

        rr = self.filtered_roadsters[self.selected_index]
        resp = QMessageBox.question(
            self,
            "Delete roadster",
            f"Delete roadster #{rr.roadster_id}?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        try:
            self.roadsters_repo.delete_by_id(rr.roadster_id)
        except Exception as e:
            QMessageBox.critical(self, "Database error", f"Unable to delete:\n{e}")
            return

        self.set_status(f"Deleted roadster #{rr.roadster_id}.")
        self.refresh_roadsters()
        self.reset_form()
