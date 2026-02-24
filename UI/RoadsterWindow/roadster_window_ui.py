from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox,
    QFrame, QScrollArea
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
class RoadsterWindowUIRefs:
    team_combo: QComboBox
    d1_combo: QComboBox
    d2_combo: QComboBox

    reset_btn: QPushButton
    delete_btn: QPushButton
    save_btn: QPushButton

    # list
    search_team_combo: QComboBox
    scroll_area: QScrollArea
    scroll_container: QWidget
    scroll_layout: QVBoxLayout

    status_label: QLabel


class RoadsterWindowUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RoadsterWindowUI")
        self.setWindowTitle("E-Horizon • Roadsters")
        self.setMinimumSize(980, 520)

        self.setStyleSheet("""
            QWidget#RoadsterWindowUI {
                background: #070B12;
                color: #EAF2FF;
                font-family: "Google Sans";
                font-size: 10pt;
            }
            QLabel { background: transparent; }
            QLabel#Title {
                font-family: "Audiowide";
                font-size: 18pt;
                letter-spacing: 1px;
            }
            QLabel#SectionTitle { font-size: 11pt; font-weight: 600; }
            QLabel#FieldLabel { color: #A8B3C7; font-size: 10pt; }

            QComboBox {
                height: 38px;
                border-radius: 14px;
                padding: 0 10px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 10pt;
            }
            QComboBox::drop-down { border: none; width: 28px; }
            QComboBox QAbstractItemView {
                background: #0E1522;
                border: 1px solid #1A2433;
                selection-background-color: #121B2B;
                color: #EAF2FF;
            }

            QPushButton {
                border-radius: 14px;
                padding: 10px 12px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 10pt;
            }
            QPushButton:hover { background: #121B2B; border: 1px solid rgba(0,166,255,0.65); }

            QPushButton#DeleteBtn {
                background: #1A1014;
                border: 1px solid #3A1F2A;
                color: #FFD6DE;
            }
            QPushButton#DeleteBtn:hover { background: #24141A; }

            QPushButton#Primary {
                background: #0B2A3A;
                border: 1px solid #00A6FF;
            }
            QPushButton#Primary:hover { background: #0D3448; }

            QLabel#Status { color: #7F8AA1; font-size: 9pt; }

            QPushButton#RoadsterRow {
                text-align: left;
                height: 40px;
                padding-left: 12px;
                border-radius: 14px;
                background: #0C111B;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 10pt;
            }
            QPushButton#RoadsterRow:hover { background: #121B2B; }
            QPushButton#RoadsterRow[selected="true"] { border: 1px solid #00A6FF; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        # header
        header = GlassCard(self, radius=22)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(18, 16, 18, 16)
        title = QLabel("ROADSTERS")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        hl.addWidget(title)
        root.addWidget(header)

        content = QHBoxLayout()
        content.setSpacing(24)

        # LEFT: form
        form = GlassCard(self, radius=22)
        fl = QVBoxLayout(form)
        fl.setContentsMargins(18, 16, 18, 18)
        fl.setSpacing(10)

        st = QLabel("Creazione / Modifica")
        st.setObjectName("SectionTitle")
        fl.addWidget(st)

        def row(label_text: str):
            h = QHBoxLayout()
            h.setSpacing(12)
            lbl = QLabel(label_text)
            lbl.setObjectName("FieldLabel")
            lbl.setFixedWidth(90)
            cb = QComboBox()
            h.addWidget(lbl)
            h.addWidget(cb, 1)
            fl.addLayout(h)
            return cb

        team_combo = row("Team")
        d1_combo = row("Driver 1")
        d2_combo = row("Driver 2")

        btns = QHBoxLayout()
        btns.setSpacing(10)
        reset_btn = QPushButton("Resetta")
        delete_btn = QPushButton("Elimina")
        delete_btn.setObjectName("DeleteBtn")
        save_btn = QPushButton("Crea / Aggiorna")
        save_btn.setObjectName("Primary")
        btns.addWidget(reset_btn)
        btns.addWidget(delete_btn)
        btns.addWidget(save_btn)
        fl.addLayout(btns)

        fl.addStretch(1)

        # RIGHT: list
        lst = GlassCard(self, radius=22)
        ll = QVBoxLayout(lst)
        ll.setContentsMargins(18, 16, 18, 18)
        ll.setSpacing(10)

        lt = QLabel("Roadsters List")
        lt.setObjectName("SectionTitle")
        ll.addWidget(lt)

        # filter row (team)
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        search_team_combo = QComboBox()
        search_team_combo.setFixedWidth(220)
        search_row.addWidget(search_team_combo)
        search_row.addStretch(1)
        ll.addLayout(search_row)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #121B2B; border-radius: 5px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)

        scroll_frame = QFrame()
        scroll_frame.setStyleSheet("""
            QFrame { background: #0E1522; border: 1px solid #1A2433; border-radius: 18px; }
        """)
        outer = QVBoxLayout(scroll_frame)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setAlignment(Qt.AlignTop)


        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll_layout.addStretch(1)  # IMPORTANT: spinge gli item in alto quando c'è spazio


        outer.addWidget(scroll_container, 0, Qt.AlignTop)
        outer.addStretch(1)  # IMPORTANT: spinge tutto in alto

        scroll_area.setWidget(scroll_frame)
        ll.addWidget(scroll_area, 1)

        status = QLabel("Ready.")
        status.setObjectName("Status")
        ll.addWidget(status)

        content.addWidget(form, 1)
        content.addWidget(lst, 1)
        root.addLayout(content, 1)

        self.refs = RoadsterWindowUIRefs(
            team_combo=team_combo,
            d1_combo=d1_combo,
            d2_combo=d2_combo,
            reset_btn=reset_btn,
            delete_btn=delete_btn,
            save_btn=save_btn,
            search_team_combo=search_team_combo,
            scroll_area=scroll_area,
            scroll_container=scroll_container,
            scroll_layout=scroll_layout,
            status_label=status,
        )
