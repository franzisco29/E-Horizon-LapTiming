from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dataclasses import replace
from PySide6.QtCore import QTimer

from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, Signal
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QWidget, QMessageBox, QFileDialog, QStyledItemDelegate,
    QSpinBox, QHeaderView, QAbstractItemView
)

from Modules.config_manager import Settings
from UI.GridWindow.grid_window_ui import GridWindowUI
from Classes.grid_generator import GridGenerator , GridDriver        # <--- adatta import dove sta GridDriver


# ----------------------------
# Table row view-model
# ----------------------------
@dataclass
class GridRow:
    position: int
    race_number: int
    driver_display: str
    team: str
    best_lap: str
    drop: int
    pit: bool


# ----------------------------
# Drop delegate (0..99)
# ----------------------------
class DropDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        sb = QSpinBox(parent)
        sb.setRange(0, 99)
        sb.setFrame(False)
        return sb

    def setEditorData(self, editor, index):
        val = index.data(Qt.EditRole)
        try:
            editor.setValue(int(val))
        except Exception:
            editor.setValue(0)

    def setModelData(self, editor, model, index):
        model.setData(index, int(editor.value()), Qt.EditRole)


# ----------------------------
# Model
# ----------------------------
class GridTableModel(QAbstractTableModel):
    dropChanged = Signal(int, int)  # race_number, new_drop

    COLS = ["Pos", "#", "Driver", "Team", "Best", "Drop", "PIT"]

    def __init__(self):
        super().__init__()
        self._rows: List[GridRow] = []

    def set_rows(self, rows: List[GridRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.COLS[section]
        return str(section + 1)

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags

        col = index.column()
        base = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        # editabile solo Drop
        if self.COLS[col] == "Drop":
            return base | Qt.ItemIsEditable
        return base

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        r = self._rows[index.row()]
        col = self.COLS[index.column()]

        # Row coloring (come VB)
        if role == Qt.BackgroundRole:
            if r.pit:
                return QColor(60, 18, 22)     # rosso scuro soft
            if r.drop > 0:
                return QColor(52, 46, 10)     # giallo scuro soft
            return QColor(14, 21, 34)         # base table bg

        if role in (Qt.DisplayRole, Qt.EditRole):
            if col == "Pos":
                return r.position
            if col == "#":
                return r.race_number
            if col == "Driver":
                return r.driver_display
            if col == "Team":
                return r.team
            if col == "Best":
                return r.best_lap
            if col == "Drop":
                return r.drop
            if col == "PIT":
                return "✓" if r.pit else ""
        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False

        col = self.COLS[index.column()]
        if col != "Drop":
            return False

        try:
            v = int(value)
        except Exception:
            v = 0

        v = max(0, min(99, v))

        row = self._rows[index.row()]
        if row.drop == v:
            return True

        # aggiorna solo il view-model, la logica aggiorna _working_grid in GridWindow
        row.drop = v
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole, Qt.BackgroundRole])
        self.dropChanged.emit(row.race_number, v)
        return True


# ----------------------------
# Window
# ----------------------------
class GridWindow(QDialog):
    def __init__(self, parent: QWidget, settings: Settings):
        super().__init__(parent)
        self.settings = settings

        self.ui = GridWindowUI(self)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.addWidget(self.ui)

        self.setWindowTitle(self.ui.windowTitle())
        self.setMinimumSize(self.ui.minimumSize())
        self.resize(self.ui.size())

        self.gen = GridGenerator()

        self._base_grid: List[GridDriver] = []
        self._working_grid: List[GridDriver] = []
        self._endurance_grid: List[GridDriver] = []  # se ce l’hai, altrimenti copia base

        self.model = GridTableModel()
        self.ui.refs.table.setModel(self.model)
        self.ui.refs.table.setItemDelegateForColumn(5, DropDelegate(self))  # Drop col = 5

        t = self.ui.refs.table
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        t.horizontalHeader().setStretchLastSection(True)

        # widths coerenti col VB
        t.setColumnWidth(0, 50)   # Pos
        t.setColumnWidth(1, 55)   # #
        t.setColumnWidth(2, 260)  # Driver
        t.setColumnWidth(3, 220)  # Team
        t.setColumnWidth(4, 110)  # Best
        t.setColumnWidth(5, 70)   # Drop
        t.setColumnWidth(6, 60)   # PIT

        # bindings
        r = self.ui.refs
        r.btn_load.clicked.connect(self.load_grid_json)
        r.btn_reset.clicked.connect(self.reset_drops)
        r.btn_pdf.clicked.connect(self.generate_pdf)

        self.model.dropChanged.connect(self.on_drop_changed)
        t.selectionModel().currentRowChanged.connect(self.on_row_changed)

        # status
        self.set_info("Load a grid JSON to start.")

    # ----------------------------
    # UI helpers
    # ----------------------------
    def set_info(self, text: str) -> None:
        self.ui.refs.info.setText(text)

    # ----------------------------
    # Loading
    # ----------------------------
    def load_grid_json(self) -> None:
        self.gen = GridGenerator()

        base_grid = self.gen.load_starting_grid_for_view(self.settings.root_path, parent=self)
        if not base_grid:
            # annullato
            self.close()
            return

        self._base_grid = base_grid
        self._working_grid = [replace(d) for d in self._base_grid]  # clone
        # endurance: per ora identica alla base (poi la colleghiamo alla tua endurance list)
        self._endurance_grid = [self._clone_driver(d) for d in base_grid]

        self.refresh_preview(keep_race_number=None)
        self.set_info(f"Loaded {len(self._base_grid)} drivers from JSON.")

    # ----------------------------
    # Preview refresh
    # ----------------------------
    def refresh_preview(self, keep_race_number: Optional[int]) -> None:
        if not self._working_grid:
            self.model.set_rows([])
            return

        final_list = self.gen.apply_penalties_and_pit_lane(self._working_grid)

        rows: List[GridRow] = []
        for d in final_list:
            rows.append(
                GridRow(
                    position=int(d.position),
                    race_number=int(d.race_number),
                    driver_display=d.name_surname(),
                    team=str(d.team),
                    best_lap=str(d.best_lap),
                    drop=int(d.grid_drop),
                    pit=bool(d.pit_lane_start),
                )
            )

        self.model.set_rows(rows)

        # reselect
        if keep_race_number is not None:
            self._select_race_number(keep_race_number)

    def _select_race_number(self, rn: int) -> None:
        t = self.ui.refs.table
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, 1)  # race number column
            if int(idx.data(Qt.DisplayRole)) == rn:
                t.selectRow(row)
                # focus on Drop
                t.setCurrentIndex(self.model.index(row, 5))
                return

    # ----------------------------
    # Events
    # ----------------------------
    def on_row_changed(self, current, previous):
        if not current.isValid():
            return
        row = current.row()
        rn = self.model.index(row, 1).data(Qt.DisplayRole)
        drv = self.model.index(row, 2).data(Qt.DisplayRole)
        self.set_info(f"Selected: #{int(rn):02d}  {drv}")


    def on_drop_changed(self, race_number: int, new_drop: int) -> None:
        drv = next((d for d in self._working_grid if int(d.race_number) == int(race_number)), None)
        if not drv:
            return
        drv.grid_drop = int(new_drop)

        rn = int(race_number)
        QTimer.singleShot(0, lambda: self.refresh_preview(keep_race_number=rn))

    # ----------------------------
    # Actions
    # ----------------------------
    def reset_drops(self) -> None:
        if not self._working_grid:
            return
        self._working_grid = [replace(d, grid_drop=0) for d in self._base_grid]
        self.refresh_preview(keep_race_number=None)
        self.set_info("Drops reset.")

    def generate_pdf(self) -> None:
        if not self._working_grid:
            QMessageBox.information(self, "PDF", "Load a grid first.")
            return

        # final list applicata
        final_list = self.gen.apply_penalties_and_pit_lane(self._working_grid)

        grids_dir = Path(self.settings.root_path) / "Grids"
        grids_dir.mkdir(parents=True, exist_ok=True)

        from datetime import datetime
        file_name = f"Final_Starting_Grid_{datetime.now():%d-%m-%Y}.pdf"
        out_pdf = grids_dir / file_name

        try:
            # endurance_grid: per ora _endurance_grid (poi la colleghiamo alla tua endurance list reale)
            self.gen.generate_pdf(final_list, out_pdf, self._endurance_grid, logo_path=None)
        except Exception as e:
            QMessageBox.critical(self, "PDF error", f"Unable to generate PDF:\n{e}")
            return

        QMessageBox.information(self, "PDF", f"PDF generated:\n{out_pdf}")
        # opzionale: apri file
        try:
            import os
            os.startfile(str(out_pdf))  # Windows
        except Exception:
            pass

    # ----------------------------
    # Helpers
    # ----------------------------
    @staticmethod
    def _clone_driver(d: GridDriver) -> GridDriver:
        return GridDriver(
            name=d.name,
            surname=d.surname,
            race_number=int(d.race_number),
            team=d.team,
            position=int(d.position),
            best_lap=d.best_lap,
            grid_drop=int(getattr(d, "grid_drop", 0)),
            desired_pos_after_penalty=int(getattr(d, "desired_pos_after_penalty", 0)),
            pit_lane_start=bool(getattr(d, "pit_lane_start", False)),
        )
