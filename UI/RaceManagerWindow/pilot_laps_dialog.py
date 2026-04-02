from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QPushButton, QMessageBox, QSizePolicy,
)

from Classes.driver import Driver
from Modules.log_utils import log
from Modules.time_format import fmt_mm_ss_mmm


class PilotLapsDialog(QDialog):
    """
    Dialog per visualizzare, annullare e ripristinare i giri di un singolo pilota.
    Aperto tramite doppio click sulla riga del pilota nella tabella principale.
    """

    sig_laps_changed = Signal()

    # ------------------------------------------------------------------
    # Stile UI
    # ------------------------------------------------------------------
    _STYLE = """
        QDialog {
            background: #1a1c1f;
            color: #e9eef5;
            font-size: 12px;
        }
        QLabel#pilot_title {
            font-size: 15px;
            font-weight: bold;
            color: #58a6ff;
            padding: 4px 0px;
        }
        QLabel#section_label {
            font-size: 11px;
            font-weight: bold;
            color: #8b9ab0;
            padding-top: 8px;
            padding-bottom: 2px;
        }
        QTableWidget {
            background: #111316;
            color: #e9eef5;
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 6px;
            gridline-color: rgba(255,255,255,0.06);
            selection-background-color: rgba(88,166,255,0.18);
        }
        QHeaderView::section {
            background: #1e2128;
            color: #8b9ab0;
            border: none;
            padding: 4px;
            font-size: 11px;
        }
        QPushButton {
            background: #21262d;
            color: #e9eef5;
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 5px;
            padding: 6px 14px;
            font-size: 12px;
        }
        QPushButton:hover {
            background: #2d333b;
        }
        QPushButton:pressed {
            background: #161b22;
        }
        QPushButton#cancel_btn {
            background: #6e1313;
            color: #ffb0b0;
            border-color: #8b2020;
        }
        QPushButton#cancel_btn:hover {
            background: #8b2020;
        }
        QPushButton#restore_btn {
            background: #0d3a1f;
            color: #7ee8a2;
            border-color: #1a5c36;
        }
        QPushButton#restore_btn:hover {
            background: #1a5c36;
        }
    """

    def __init__(self, driver: Driver, race: bool, parent=None) -> None:
        super().__init__(parent)
        self.driver = driver
        self.race = race

        self.setWindowTitle(f"Giri pilota — {driver.name} {driver.surname}")
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        self.setStyleSheet(self._STYLE)
        self.setWindowFlags(self.windowFlags() | Qt.Window)

        self._build_ui()
        self._populate_active()
        self._populate_cancelled()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(6)

        # Titolo
        title = QLabel(f"{self.driver.name} {self.driver.surname}  —  #{self.driver.race_number}")
        title.setObjectName("pilot_title")
        root.addWidget(title)

        # ---- Sezione giri ATTIVI ----
        lbl_active = QLabel("Giri attivi")
        lbl_active.setObjectName("section_label")
        root.addWidget(lbl_active)

        self.active_table = self._make_table()
        root.addWidget(self.active_table)

        btn_cancel = QPushButton("Annulla giri selezionati")
        btn_cancel.setObjectName("cancel_btn")
        btn_cancel.clicked.connect(self._on_cancel_clicked)
        root.addWidget(btn_cancel, alignment=Qt.AlignRight)

        # ---- Sezione giri ANNULLATI ----
        lbl_cancelled = QLabel("Giri annullati")
        lbl_cancelled.setObjectName("section_label")
        root.addWidget(lbl_cancelled)

        self.cancelled_table = self._make_table()
        root.addWidget(self.cancelled_table)

        btn_restore = QPushButton("Ripristina giri selezionati")
        btn_restore.setObjectName("restore_btn")
        btn_restore.clicked.connect(self._on_restore_clicked)
        root.addWidget(btn_restore, alignment=Qt.AlignRight)

        # ---- Chiudi ----
        btn_close = QPushButton("Chiudi")
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close, alignment=Qt.AlignRight)

    def _make_table(self) -> QTableWidget:
        t = QTableWidget(0, 2)
        t.setHorizontalHeaderLabels(["Giro #", "Tempo"])
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.MultiSelection)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.horizontalHeader().setHighlightSections(False)
        t.setMinimumHeight(150)
        t.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return t

    # ------------------------------------------------------------------
    # Populate
    # ------------------------------------------------------------------
    def refresh_laps(self) -> None:
        """
        Aggiorna entrambe le tabelle senza chiudere la dialog.
        Chiamato automaticamente quando arriva un nuovo giro per questo pilota.
        """
        self._populate_active()
        self._populate_cancelled()

    def _populate_active(self) -> None:
        t = self.active_table
        t.setRowCount(0)
        for i, td in enumerate(self.driver.lap_history):
            r = t.rowCount()
            t.insertRow(r)
            t.setItem(r, 0, self._centered_item(str(i + 1)))
            t.setItem(r, 1, self._centered_item(fmt_mm_ss_mmm(td)))

    def _populate_cancelled(self) -> None:
        t = self.cancelled_table
        t.setRowCount(0)
        for ci, (orig_pos, td) in enumerate(self.driver.cancelled_laps):
            r = t.rowCount()
            t.insertRow(r)
            t.setItem(r, 0, self._centered_item(f"#{orig_pos + 1}"))
            t.setItem(r, 1, self._centered_item(fmt_mm_ss_mmm(td)))

    @staticmethod
    def _centered_item(text: str) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setTextAlignment(int(Qt.AlignCenter))
        return it

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_cancel_clicked(self) -> None:
        selected_rows = sorted(set(i.row() for i in self.active_table.selectedItems()))
        if not selected_rows:
            QMessageBox.information(self, "Nessuna selezione", "Seleziona uno o più giri da annullare.")
            return

        # Build preview text
        lines = []
        for r in selected_rows:
            num = self.active_table.item(r, 0).text()
            t = self.active_table.item(r, 1).text()
            lines.append(f"  Giro {num}  —  {t}")
        preview = "\n".join(lines)

        reply = QMessageBox.question(
            self,
            "Conferma annullamento",
            f"Annullare i seguenti giri di {self.driver.name} {self.driver.surname}?\n\n{preview}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.driver.cancel_laps(selected_rows, self.race)

        driver_label = f"{self.driver.name} {self.driver.surname} (#{self.driver.race_number})"
        times = [lines[i] for i in range(len(selected_rows))]
        log(f"[DIALOGO_GIRI] Annullamento giri — pilota={driver_label} | giri: {times}")

        self._populate_active()
        self._populate_cancelled()
        self.sig_laps_changed.emit()

    def _on_restore_clicked(self) -> None:
        selected_rows = sorted(set(i.row() for i in self.cancelled_table.selectedItems()))
        if not selected_rows:
            QMessageBox.information(self, "Nessuna selezione", "Seleziona uno o più giri da ripristinare.")
            return

        lines = []
        for r in selected_rows:
            num = self.cancelled_table.item(r, 0).text()
            t = self.cancelled_table.item(r, 1).text()
            lines.append(f"  Giro orig. {num}  —  {t}")
        preview = "\n".join(lines)

        reply = QMessageBox.question(
            self,
            "Conferma ripristino",
            f"Ripristinare i seguenti giri di {self.driver.name} {self.driver.surname}?\n\n{preview}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.driver.restore_laps(selected_rows, self.race)

        driver_label = f"{self.driver.name} {self.driver.surname} (#{self.driver.race_number})"
        times = [lines[i] for i in range(len(selected_rows))]
        log(f"[DIALOGO_GIRI] Ripristino giri — pilota={driver_label} | giri: {times}")

        self._populate_active()
        self._populate_cancelled()
        self.sig_laps_changed.emit()
