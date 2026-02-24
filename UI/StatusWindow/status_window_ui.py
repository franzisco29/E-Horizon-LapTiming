from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


@dataclass
class StatusWindowUIRefs:
    conn_label: QLabel
    status_label: QLabel


class StatusWindowUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusWindowUI")
        self.setStyleSheet("""
            QWidget#StatusWindowUI {
                background: #070B12;
                color: #EAF2FF;
                font-family: "Google Sans";
                font-size: 10pt;
            }
            QLabel { background: transparent; }
            QLabel#Conn {
                color: #A8B3C7;
                font-size: 10pt;
                font-weight: 600;
            }
            QLabel#Status {
                color: #EAF2FF;
                font-size: 10pt;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        conn_label = QLabel("Connect to: -/-")
        conn_label.setObjectName("Conn")
        conn_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        status_label = QLabel("")
        status_label.setObjectName("Status")
        status_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        status_label.setWordWrap(True)

        root.addWidget(conn_label)
        root.addWidget(status_label, 1)

        self.refs = StatusWindowUIRefs(
            conn_label=conn_label,
            status_label=status_label,
        )