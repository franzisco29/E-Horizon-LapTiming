from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableView, QSizePolicy
)


class GlassCard(QFrame):
    def __init__(self, parent=None, radius: int = 22):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame#GlassCard {{
                background: #0C111B;
                border: 1px solid #1A2433;
                border-radius: {radius}px;
            }}
        """)


@dataclass
class GridWindowUIRefs:
    title: QLabel
    table: QTableView
    btn_load: QPushButton
    btn_reset: QPushButton
    btn_pdf: QPushButton
    info: QLabel


class GridWindowUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GridWindowUI")
        self.setWindowTitle("E-Horizon • Grid Preview")
        self.setMinimumSize(1050, 650)

        self.setStyleSheet("""
            QWidget#GridWindowUI {
                background: #070B12;
                color: #EAF2FF;
                font-family: "Google Sans";
                font-size: 10pt;
            }
            QLabel { background: transparent; }

            QLabel#Title {
                font-family: "Audiowide";
                font-size: 20pt;
                letter-spacing: 1px;
            }

            QFrame#GlassCard {
                background: #0C111B;
                border: 1px solid #1A2433;
                border-radius: 22px;
            }

            QPushButton {
                border-radius: 14px;
                padding: 10px 12px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 10pt;
            }
            QPushButton:hover {
                background: #121B2B;
                border: 1px solid rgba(0,166,255,0.65);
            }
            QPushButton#Primary {
                background: #0B2A3A;
                border: 1px solid #00A6FF;
                font-weight: 600;
            }
            QPushButton#Primary:hover { background: #0D3448; }

            QLabel#Hint {
                color: #A8B3C7;
                font-size: 9pt;
            }

            /* Table */
            QTableView {
                background: #0E1522;
                border: 1px solid #1A2433;
                border-radius: 18px;
                gridline-color: #1A2433;
                selection-background-color: rgba(0,166,255,0.22);
                selection-color: #EAF2FF;
                outline: 0;
            }
            QHeaderView::section {
                background: #0C111B;
                color: #EAF2FF;
                border: none;
                border-bottom: 1px solid #1A2433;
                padding: 8px 10px;
                font-weight: 700;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        # Header
        header = GlassCard(self, radius=22)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(18, 16, 18, 16)

        title = QLabel("GRID PREVIEW")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        hl.addWidget(title)
        root.addWidget(header)

        # Top controls
        controls = GlassCard(self, radius=22)
        cl = QHBoxLayout(controls)
        cl.setContentsMargins(18, 12, 18, 12)
        cl.setSpacing(10)

        btn_load = QPushButton("📂 Load Grid JSON")
        btn_reset = QPushButton("↺ Reset Drops")
        btn_pdf = QPushButton("🧾 Generate PDF (Final + Sprint + Endurance)")
        btn_pdf.setObjectName("Primary")

        hint = QLabel("Edit 'Drop' (0–99). PIT is computed automatically.")
        hint.setObjectName("Hint")
        hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        cl.addWidget(btn_load)
        cl.addWidget(btn_reset)
        cl.addWidget(btn_pdf)
        cl.addWidget(hint, 1)
        root.addWidget(controls)

        # Table
        table_card = GlassCard(self, radius=22)
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(14, 14, 14, 14)
        table = QTableView()
        table.setSortingEnabled(False)
        table.setAlternatingRowColors(False)
        tl.addWidget(table)
        root.addWidget(table_card, 1)

        # Bottom info
        info = QLabel("Ready.")
        info.setObjectName("Hint")
        root.addWidget(info)

        self.refs = GridWindowUIRefs(
            title=title,
            table=table,
            btn_load=btn_load,
            btn_reset=btn_reset,
            btn_pdf=btn_pdf,
            info=info,
        )
