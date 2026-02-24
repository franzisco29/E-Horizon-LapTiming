from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame
)


def cast_num(idx: int) -> str:
    return ["Lap Done", "S1", "S2", "Pit In", "Pit Out"][idx] if 0 <= idx <= 4 else "Error"


@dataclass
class DebugWindowUIRefs:
    scroll_area: QScrollArea
    rows_container: QWidget
    rows_layout: QVBoxLayout


class DebugWindowUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DebugWindowUI")
        self.setStyleSheet("""
            QWidget#DebugWindowUI {
                background: #070B12;
                color: #EAF2FF;
                font-family: "Google Sans";
                font-size: 10pt;
            }
            QLabel { background: transparent; }
            QLabel#Title {
                font-family: "Audiowide";
                font-size: 14pt;
                letter-spacing: 1px;
            }
            QFrame#RowCard {
                background: #0C111B;
                border: 1px solid #1A2433;
                border-radius: 16px;
            }
            QLabel#DriverName {
                color: #EAF2FF;
                font-weight: 600;
            }
            QPushButton {
                height: 36px;
                border-radius: 12px;
                padding: 0 10px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 9pt;
                text-align: center;
            }
            QPushButton:hover {
                background: #121B2B;
                border: 1px solid rgba(0,166,255,0.65);
            }
            QScrollArea { background: transparent; }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #121B2B;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        title = QLabel("DEBUG • SIMULATE TRANSPONDERS")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        outer_frame = QFrame()
        outer_frame.setStyleSheet("QFrame{ background: transparent; }")
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        rows_container = QWidget()
        rows_layout = QVBoxLayout(rows_container)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(10)
        rows_layout.addStretch(1)

        outer_layout.addWidget(rows_container)
        scroll_area.setWidget(outer_frame)

        root.addWidget(scroll_area, 1)

        self.refs = DebugWindowUIRefs(
            scroll_area=scroll_area,
            rows_container=rows_container,
            rows_layout=rows_layout,
        )

    # ---------
    # UI helpers
    # ---------
    def clear_rows(self) -> None:
        layout = self.refs.rows_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        layout.addStretch(1)

    def add_row(
        self,
        driver_label: str,
        number: int,
        on_click_factory,
    ) -> None:
        """
        on_click_factory(device:int, number:int) -> callable
        """
        card = QFrame()
        card.setObjectName("RowCard")
        hl = QHBoxLayout(card)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(10)

        lbl = QLabel(driver_label)
        lbl.setObjectName("DriverName")
        lbl.setMinimumWidth(260)
        hl.addWidget(lbl, 1)

        for device in range(5):
            btn = QPushButton(cast_num(device))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(on_click_factory(device, number))
            hl.addWidget(btn, 0)

        # inserisci prima dello stretch finale
        layout = self.refs.rows_layout
        layout.insertWidget(max(0, layout.count() - 1), card)