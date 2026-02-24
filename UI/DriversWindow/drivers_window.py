from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
    QPushButton,
    QLabel,
    QWidget,
    QVBoxLayout,
)

from Modules.db import Database, db_path_from_root, init_db
from Modules.repositories.drivers_repo import DriversRepo, DriverRow
from Modules.config_manager import Settings
from UI.DriversWindow.drivers_window_ui import DriversWindowUI


class DriversWindow(QDialog):
    """
    Clean version:
    - store selection as driver_id (stable across filtering/sorting)
    - selection is optional (None = create new)
    - keep list rendering simple + deterministic
    """

    def __init__(self, parent: QWidget | None, settings: Settings):
        super().__init__(parent)
        self.settings = settings

        # --- resolve root path from Settings
        root_path = getattr(self.settings, "root_path", None)
        if not root_path and hasattr(self.settings, "paths"):
            root_path = getattr(self.settings.paths, "root_path", None)
        if not root_path:
            raise ValueError(
                "Settings root_path not found (expected settings.root_path or settings.paths.root_path)."
            )

        # --- DB + repo
        db_path = db_path_from_root(root_path, filename="ehorizon.db")
        self.db = Database(db_path)
        init_db(self.db)
        self.repo = DriversRepo(self.db)

        # Optional: one-shot legacy migration
        # self.repo.migrate_from_legacy_txt_once(root_path)

        # --- UI hosted inside the dialog
        self.ui = DriversWindowUI(self)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.addWidget(self.ui)

        self.setWindowTitle(self.ui.windowTitle())
        self.setMinimumSize(self.ui.minimumSize())
        self.resize(self.ui.size())

        # --- state
        self.all_drivers: List[DriverRow] = []
        self.filtered: List[DriverRow] = []
        self.selected_driver_id: Optional[int] = None
        self._row_buttons: List[QPushButton] = []
        self._row_ids: List[int] = []  # index -> driver_id for the rendered list

        # --- bindings
        r = self.ui.refs
        r.refresh_btn.clicked.connect(self.refresh)
        r.reset_btn.clicked.connect(self.reset_form)
        r.save_btn.clicked.connect(self.create_or_update)
        r.delete_btn.clicked.connect(self.delete_selected)

        r.filter_option.currentIndexChanged.connect(lambda _i: self.apply_filter())
        r.search_entry.textChanged.connect(lambda _t: self.apply_filter())

        # click outside row buttons => deselect
        r.scroll_area.viewport().installEventFilter(self)

        # init
        self.refresh()

    # -------------------------
    # Qt event filter
    # -------------------------
    def eventFilter(self, obj, event):
        if obj is self.ui.refs.scroll_area.viewport() and event.type() == QEvent.MouseButtonPress:
            try:
                pos = event.position().toPoint()
            except Exception:
                pos = event.pos()

            w = obj.childAt(pos)
            if not (isinstance(w, QPushButton) and w.objectName() == "DriverRow"):
                self.deselect_driver()

        return super().eventFilter(obj, event)

    # -------------------------
    # Helpers
    # -------------------------
    def set_status(self, text: str) -> None:
        self.ui.refs.status_label.setText(text)

    def _get_selected_row(self) -> Optional[DriverRow]:
        if self.selected_driver_id is None:
            return None
        return next((d for d in self.all_drivers if d.driver_id == self.selected_driver_id), None)

    def reset_form(self) -> None:
        r = self.ui.refs
        r.name_entry.clear()
        r.surname_entry.clear()
        r.team_entry.clear()
        r.transponder_entry.clear()
        r.race_number_entry.clear()
        r.pro_checkbox.setChecked(False)

        self.selected_driver_id = None
        self.highlight_selected()
        self.set_status("Ready (new driver).")

    def fill_form(self, d: DriverRow) -> None:
        r = self.ui.refs
        r.name_entry.setText(d.name)
        r.surname_entry.setText(d.surname)
        r.team_entry.setText(d.team)
        r.transponder_entry.setText(str(d.transponder_id))
        r.race_number_entry.setText(str(d.race_number))
        r.pro_checkbox.setChecked(bool(d.pro))

    def _parse_int_field(self, label: str, value: str) -> Optional[int]:
        try:
            return int(value)
        except Exception:
            QMessageBox.warning(self, "Invalid value", f"{label} must be a number.")
            return None

    def parse_form(self) -> Optional[DriverRow]:
        r = self.ui.refs

        name = r.name_entry.text().strip()
        surname = r.surname_entry.text().strip()
        team = r.team_entry.text().strip()
        pro = bool(r.pro_checkbox.isChecked())

        if not name or not surname or not team:
            QMessageBox.warning(self, "Missing fields", "Name, Surname and Team are required.")
            return None

        transponder_id = self._parse_int_field("Transponder ID", r.transponder_entry.text().strip())
        if transponder_id is None:
            return None

        race_number = self._parse_int_field("Race Number", r.race_number_entry.text().strip())
        if race_number is None:
            return None

        exclude_id = self.selected_driver_id
        t_used, r_used = self.repo.conflicts(
            transponder_id=transponder_id,
            race_number=race_number,
            exclude_id=exclude_id,
        )
        if t_used:
            QMessageBox.warning(self, "Duplicate", "Transponder ID already used.")
            return None
        if r_used:
            QMessageBox.warning(self, "Duplicate", "Race Number already used.")
            return None

        return DriverRow(
            driver_id=self.selected_driver_id or 0,  # repo can ignore/replace on insert
            name=name,
            surname=surname,
            team=team,
            transponder_id=transponder_id,
            pro=pro,
            race_number=race_number,
        )

    # -------------------------
    # Data + list
    # -------------------------
    def refresh(self) -> None:
        self.all_drivers = self.repo.get_all()

        # if current selection was deleted externally, drop it
        if self.selected_driver_id is not None:
            if not any(d.driver_id == self.selected_driver_id for d in self.all_drivers):
                self.selected_driver_id = None

        self.apply_filter()
        self.set_status(f"Loaded {len(self.all_drivers)} drivers.")

    def apply_filter(self) -> None:
        r = self.ui.refs
        mode = r.filter_option.currentText()
        q = r.search_entry.text().strip().lower()

        base = self.all_drivers

        if mode == "AM (Not Pro)":
            base = [d for d in base if not d.pro]
        elif mode == "PRO":
            base = [d for d in base if d.pro]

        if q:
            def match(d: DriverRow) -> bool:
                return (
                    q in d.name.lower()
                    or q in d.surname.lower()
                    or q in d.team.lower()
                    or q in str(d.driver_id)
                    or q in str(d.transponder_id)
                    or q in str(d.race_number)
                )
            base = [d for d in base if match(d)]

        self.filtered = list(base)

        # if selected driver is not visible under current filter, keep selection
        # but it won't be highlighted in the list (that’s fine)
        self.render_list()
        self.highlight_selected()

        # if we have a selected driver and it's visible, keep form filled
        # otherwise, don't force a selection
        if self.selected_driver_id is not None:
            visible = next((d for d in self.filtered if d.driver_id == self.selected_driver_id), None)
            if visible is not None:
                self.fill_form(visible)

        if not self.filtered:
            self.set_status("No drivers found.")

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
            empty = QLabel("No drivers found.")
            empty.setStyleSheet("color:#7F8AA1; font-size:12px;")
            layout.addWidget(empty)
            layout.addStretch(1)
            return

        for d in self.filtered:
            btn = QPushButton(d.display())
            btn.setObjectName("DriverRow")
            btn.setProperty("selected", False)
            btn.setCursor(Qt.PointingHandCursor)

            driver_id = d.driver_id
            btn.clicked.connect(lambda _checked=False, did=driver_id: self.select_driver(did))

            layout.addWidget(btn)
            self._row_buttons.append(btn)
            self._row_ids.append(driver_id)

        layout.addStretch(1)

    def highlight_selected(self) -> None:
        for btn, did in zip(self._row_buttons, self._row_ids):
            btn.setProperty("selected", did == self.selected_driver_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def select_driver(self, driver_id: int) -> None:
        d = next((x for x in self.filtered if x.driver_id == driver_id), None)
        if d is None:
            # might be filtered out or stale
            d = next((x for x in self.all_drivers if x.driver_id == driver_id), None)
        if d is None:
            return

        self.selected_driver_id = d.driver_id
        self.fill_form(d)
        self.highlight_selected()
        self.set_status(f"Selected: {d.display()}")

    def deselect_driver(self) -> None:
        self.selected_driver_id = None
        self.reset_form()
        # reset_form already highlights + status, but keep consistent:
        self.highlight_selected()

    # -------------------------
    # CRUD
    # -------------------------
    def create_or_update(self) -> None:
        row = self.parse_form()
        if not row:
            return

        try:
            new_id = self.repo.upsert(row)
        except Exception as e:
            QMessageBox.critical(self, "Database error", f"Unable to save driver:\n{e}")
            return

        self.set_status(f"Saved driver #{new_id}.")
        self.refresh()

        # per tua richiesta: dopo save reset sempre
        self.reset_form()

    def delete_selected(self) -> None:
        if self.selected_driver_id is None:
            QMessageBox.information(self, "Delete", "Select a driver first.")
            return

        d = next((x for x in self.all_drivers if x.driver_id == self.selected_driver_id), None)
        if d is None:
            self.selected_driver_id = None
            self.refresh()
            return

        resp = QMessageBox.question(
            self,
            "Delete driver",
            f"Delete driver:\n\n{d.display()}\n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        try:
            self.repo.delete_by_id(d.driver_id)
        except Exception as e:
            QMessageBox.critical(self, "Database error", f"Unable to delete driver:\n{e}")
            return

        self.selected_driver_id = None
        self.set_status(f"Deleted driver #{d.driver_id}.")
        self.refresh()
        self.reset_form()

    # -------------------------
    # Navigation (optional)
    # -------------------------
    def prev_driver(self) -> None:
        if not self.filtered:
            return

        if self.selected_driver_id is None:
            self.select_driver(self.filtered[0].driver_id)
            return

        ids = [d.driver_id for d in self.filtered]
        if self.selected_driver_id not in ids:
            self.select_driver(self.filtered[0].driver_id)
            return

        i = ids.index(self.selected_driver_id)
        self.select_driver(ids[(i - 1) % len(ids)])

    def next_driver(self) -> None:
        if not self.filtered:
            return

        if self.selected_driver_id is None:
            self.select_driver(self.filtered[0].driver_id)
            return

        ids = [d.driver_id for d in self.filtered]
        if self.selected_driver_id not in ids:
            self.select_driver(self.filtered[0].driver_id)
            return

        i = ids.index(self.selected_driver_id)
        self.select_driver(ids[(i + 1) % len(ids)])