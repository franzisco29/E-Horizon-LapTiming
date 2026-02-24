# UI/RaceListWindow/racelist_window.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout, QMessageBox, QPushButton, QCheckBox

from Modules.config_manager import Settings
from Modules.db import Database, db_path_from_root, init_db
from Modules.repositories.drivers_repo import DriversRepo
from Modules.repositories.roadsters_repo import RoadstersRepo, RoadsterRow
from Modules.repositories.racelists_repo import RaceListsRepo, RaceListRow
from UI.RaceListWindow.racelist_window_ui import RaceListWindowUI


@dataclass
class _AvailItem:
    kind: str  # "driver" | "roadster"
    id: int
    label: str


class RaceListWindow(QDialog):
    def __init__(self, parent: QWidget, settings: Settings):
        super().__init__(parent)
        self.settings = settings

        root_path = getattr(settings, "root_path", None) or getattr(getattr(settings, "paths", None), "root_path", None)
        if not root_path:
            raise ValueError("Settings root_path not found.")

        db_path = db_path_from_root(root_path, filename="ehorizon.db")
        self.db = Database(db_path)
        init_db(self.db)

        # repos
        self.drivers_repo = DriversRepo(self.db)
        self.roadsters_repo = RoadstersRepo(self.db)
        self.racelists_repo = RaceListsRepo(self.db)

        # UI host
        self.ui = RaceListWindowUI(self)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.addWidget(self.ui)

        self.setWindowTitle(self.ui.windowTitle())
        self.setMinimumSize(self.ui.minimumSize())
        self.resize(self.ui.size())

        # state
        self._available: List[_AvailItem] = []
        self._avail_checks: List[QCheckBox] = []
        self._lists_buttons: List[QPushButton] = []
        self._lists_cache: List[RaceListRow] = []

        self._selected_list_id: int = 0  # selected on right
        self._editing_list_id: int = 0   # currently loaded into builder

        # bindings
        r = self.ui.refs
        r.filter_combo.currentIndexChanged.connect(self.refresh_available)
        r.select_all_btn.clicked.connect(self.select_all_available)
        r.unselect_all_btn.clicked.connect(self.unselect_all_available)
        r.create_btn.clicked.connect(self.create_or_update)
        r.cancel_btn.clicked.connect(self.close)

        r.refresh_btn.clicked.connect(self.refresh_lists)
        r.new_btn.clicked.connect(self.new_list)
        r.edit_btn.clicked.connect(self.edit_selected)
        r.delete_btn.clicked.connect(self.delete_selected)

        # init
        self.refresh_available()
        self.refresh_lists()
        self.set_status("Ready.")

    # -------------------------
    # Status
    # -------------------------
    def set_status(self, t: str) -> None:
        self.ui.refs.status_label.setText(t)

    # -------------------------
    # Available (left)
    # -------------------------
    def _clear_available(self) -> None:
        layout = self.ui.refs.available_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._avail_checks.clear()

    def refresh_available(self) -> None:
        self._clear_available()
        layout = self.ui.refs.available_layout

        mode = self.ui.refs.filter_combo.currentIndex()
        # 0 all, 1 am, 2 pro, 3 roadsters
        items: List[_AvailItem] = []

        if mode == 3:
            # roadsters
            roadsters = self.roadsters_repo.list_all()
            # serve label driver1/driver2 -> prendiamo drivers
            drivers = {d.driver_id: d for d in self.drivers_repo.get_all()}
            for rs in roadsters:
                d1 = drivers.get(rs.driver1_id)
                d2 = drivers.get(rs.driver2_id)
                d1_label = f"{d1.name} {d1.surname} #{d1.race_number}" if d1 else f"#{rs.driver1_id}"
                d2_label = f"{d2.name} {d2.surname} #{d2.race_number}" if d2 else f"#{rs.driver2_id}"
                items.append(_AvailItem("roadster", rs.roadster_id, rs.display(d1_label, d2_label)))
        else:
            drivers = self.drivers_repo.get_all()
            if mode == 1:
                drivers = [d for d in drivers if not bool(d.pro)]
            elif mode == 2:
                drivers = [d for d in drivers if bool(d.pro)]

            for d in drivers:
                label = f"{d.name} {d.surname} | {d.team} | #{d.race_number} | Tras: {d.transponder_id}"
                items.append(_AvailItem("driver", d.driver_id, label))

        self._available = items

        if not items:
            lab = QCheckBox("No items.")
            lab.setEnabled(False)
            layout.addWidget(lab)
            layout.addStretch(1)
            return

        for it in items:
            cb = QCheckBox(it.label)
            cb.setProperty("item_id", it.id)
            cb.setProperty("kind", it.kind)
            layout.addWidget(cb)
            self._avail_checks.append(cb)

        layout.addStretch(1)

    def select_all_available(self) -> None:
        for cb in self._avail_checks:
            if cb.isEnabled():
                cb.setChecked(True)

    def unselect_all_available(self) -> None:
        for cb in self._avail_checks:
            if cb.isEnabled():
                cb.setChecked(False)

    def _get_selected_available_ids(self) -> Tuple[bool, List[int]]:
        """
        returns (is_endurance, ids)
        """
        mode = self.ui.refs.filter_combo.currentIndex()
        is_end = (mode == 3)

        ids: List[int] = []
        for cb in self._avail_checks:
            if cb.isChecked():
                ids.append(int(cb.property("item_id")))
        return is_end, ids

    # -------------------------
    # Lists (right)
    # -------------------------
    def _clear_lists(self) -> None:
        layout = self.ui.refs.lists_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._lists_buttons.clear()

    def refresh_lists(self) -> None:
        self._clear_lists()
        layout = self.ui.refs.lists_layout

        self._lists_cache = self.racelists_repo.list_all()

        if not self._lists_cache:
            btn = QPushButton("No lists yet.")
            btn.setEnabled(False)
            layout.addWidget(btn)
            layout.addStretch(1)
            return

        for row in self._lists_cache:
            b = QPushButton(row.display())
            b.setCursor(Qt.PointingHandCursor)
            b.setProperty("list_id", row.list_id)
            b.clicked.connect(lambda _=False, lid=row.list_id: self.select_list(lid))
            layout.addWidget(b)
            self._lists_buttons.append(b)

        layout.addStretch(1)

        # keep selection if possible
        if self._selected_list_id == 0:
            self.select_list(self._lists_cache[0].list_id)
        else:
            self.select_list(self._selected_list_id, silent=True)

    def select_list(self, list_id: int, silent: bool = False) -> None:
        self._selected_list_id = int(list_id)
        for b in self._lists_buttons:
            sel = int(b.property("list_id")) == self._selected_list_id
            b.setStyleSheet(
                "QPushButton{ text-align:left; }"
                + ("QPushButton{ border:1px solid #00A6FF; }" if sel else "")
            )
        if not silent:
            self.set_status(f"Selected list id={self._selected_list_id}")

    def new_list(self) -> None:
        self._editing_list_id = 0
        self.ui.refs.name_edit.clear()
        self.ui.refs.filter_combo.setCurrentIndex(0)
        self.unselect_all_available()
        self.set_status("New list.")

    def edit_selected(self) -> None:
        if self._selected_list_id <= 0:
            QMessageBox.information(self, "Edit", "Select a list first.")
            return

        meta = self.racelists_repo.get(self._selected_list_id)
        if not meta:
            QMessageBox.warning(self, "Edit", "List not found.")
            self.refresh_lists()
            return

        self._editing_list_id = meta.list_id
        self.ui.refs.name_edit.setText(meta.name)

        # set filter to match list type
        if meta.is_endurance:
            self.ui.refs.filter_combo.setCurrentIndex(3)
            ids = set(self.racelists_repo.get_roadster_ids(meta.list_id))
        else:
            self.ui.refs.filter_combo.setCurrentIndex(0)
            ids = set(self.racelists_repo.get_driver_ids(meta.list_id))

        # refresh_available was triggered by filter set
        for cb in self._avail_checks:
            cb_id = int(cb.property("item_id"))
            cb.setChecked(cb_id in ids)

        self.set_status(f"Editing: {meta.display()}")

    def delete_selected(self) -> None:
        if self._selected_list_id <= 0:
            QMessageBox.information(self, "Delete", "Select a list first.")
            return

        meta = self.racelists_repo.get(self._selected_list_id)
        if not meta:
            QMessageBox.warning(self, "Delete", "List not found.")
            self.refresh_lists()
            return

        resp = QMessageBox.question(
            self,
            "Delete list",
            f"Delete list:\n\n{meta.display()}\n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        self.racelists_repo.delete_by_id(meta.list_id)
        if self._editing_list_id == meta.list_id:
            self.new_list()

        self._selected_list_id = 0
        self.refresh_lists()
        self.set_status("List deleted.")

    # -------------------------
    # Create / Update
    # -------------------------
    def create_or_update(self) -> None:
        name = self.ui.refs.name_edit.text().strip()
        is_endurance, ids = self._get_selected_available_ids()

        if not name:
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        if not ids:
            QMessageBox.warning(self, "Validation", "Select at least one item.")
            return

        # (opzionale) se stai editando una lista e cambi tipo, lo permettiamo:
        # in quel caso riscrive meta + items.
        try:
            new_id = self.racelists_repo.upsert_list(
                list_id=int(self._editing_list_id),
                name=name,
                is_endurance=bool(is_endurance),
                item_ids=ids,
            )
        except Exception as e:
            QMessageBox.critical(self, "Database error", f"Unable to save list:\n{e}")
            return

        self.set_status(f"Saved list #{new_id}.")
        self._editing_list_id = 0
        self._selected_list_id = new_id
        self.refresh_lists()
        self.new_list()  # reset builder come “Create” VB (hide/clear)