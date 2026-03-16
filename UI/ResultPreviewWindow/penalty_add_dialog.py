from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class PenaltyAddDialog(QDialog):
    def __init__(self, driver_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Aggiungi penalita")
        self.setModal(True)
        self.setMinimumWidth(380)

        self._seconds = 0
        self._motivation = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        lbl = QLabel(f"Pilota: {driver_name}", self)
        lbl.setStyleSheet("font-weight: 600;")
        root.addWidget(lbl)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.seconds_edit = QLineEdit(self)
        self.seconds_edit.setPlaceholderText("Secondi (es. 5)")
        self.seconds_edit.setValidator(QIntValidator(1, 999, self.seconds_edit))

        self.motivation_edit = QLineEdit(self)
        self.motivation_edit.setPlaceholderText("Motivazione (obbligatoria)")

        form.addRow("Penalita (s)", self.seconds_edit)
        form.addRow("Motivazione", self.motivation_edit)
        root.addLayout(form)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.buttons.button(QDialogButtonBox.Ok).setText("Aggiungi")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Annulla")
        root.addWidget(self.buttons)

        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)

        # Enter: seconds -> motivation -> confirm
        self.seconds_edit.returnPressed.connect(self._on_seconds_enter)
        self.motivation_edit.returnPressed.connect(self._on_accept)

        self.seconds_edit.setFocus()

    @property
    def seconds(self) -> int:
        return self._seconds

    @property
    def motivation(self) -> str:
        return self._motivation

    def _on_seconds_enter(self) -> None:
        self.motivation_edit.setFocus()

    def _on_accept(self) -> None:
        sec_text = self.seconds_edit.text().strip()
        mot_text = self.motivation_edit.text().strip()

        try:
            sec_value = int(sec_text)
        except Exception:
            sec_value = 0

        if sec_value <= 0:
            QMessageBox.warning(self, "Penalita non valida", "Inserisci una penalita in secondi maggiore di 0.")
            self.seconds_edit.setFocus()
            self.seconds_edit.selectAll()
            return

        if not mot_text:
            QMessageBox.warning(self, "Motivazione mancante", "Inserisci la motivazione della penalita.")
            self.motivation_edit.setFocus()
            return

        self._seconds = sec_value
        self._motivation = mot_text
        self.accept()
