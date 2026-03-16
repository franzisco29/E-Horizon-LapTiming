from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class GlassCard(QFrame):
    def __init__(self, parent=None, radius: int = 22):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            f"""
            QFrame#GlassCard {{
                background: #0C111B;
                border: 1px solid #1A2433;
                border-radius: {radius}px;
            }}
            """
        )


@dataclass
class CircuitsWindowUIRefs:
    name_entry: QLineEdit
    location_entry: QLineEdit
    track_len_entry: QLineEdit
    s1_entry: QLineEdit
    s2_entry: QLineEdit
    s3_entry: QLineEdit
    notes_entry: QTextEdit

    reset_btn: QPushButton
    delete_btn: QPushButton
    save_btn: QPushButton

    search_entry: QLineEdit
    scroll_area: QScrollArea
    scroll_container: QWidget
    scroll_layout: QVBoxLayout

    status_label: QLabel


class CircuitsWindowUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CircuitsWindowUI")
        self.setWindowTitle("E-Horizon • Circuits")
        self.setMinimumSize(980, 620)
        self.resize(1120, 700)

        self.setStyleSheet(
            """
            QWidget#CircuitsWindowUI {
                background: #070B12;
                color: #EAF2FF;
                font-family: "Google Sans";
            }
            QLabel#Title { color: #EAF2FF; font-size: 28px; font-weight: 700; letter-spacing: 1px; }
            QLabel#SubTitle { color: #A8B3C7; font-size: 13px; }
            QLabel#SectionTitle { color: #EAF2FF; font-size: 15px; font-weight: 600; }
            QLabel#FieldLabel { color: #A8B3C7; font-size: 12px; }
            QLabel#Hint { color: #7F8AA1; font-size: 11px; }
            QLabel#Status { color: #7F8AA1; font-size: 11px; }
            QLineEdit {
                height: 40px;
                border-radius: 14px;
                padding: 0 12px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #00A6FF; }
            QTextEdit {
                border-radius: 14px;
                padding: 8px 10px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 12px;
            }
            QPushButton {
                border-radius: 14px;
                padding: 10px 12px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 12px;
            }
            QPushButton:hover { background: #121B2B; }
            QPushButton#DeleteBtn {
                background: #1A1014;
                border: 1px solid #3A1F2A;
                color: #FFD6DE;
            }
            QPushButton#DeleteBtn:hover { background: #24141A; }
            QPushButton#SaveBtn {
                background: #0B2A3A;
                border: 1px solid #00A6FF;
                color: #EAF2FF;
            }
            QPushButton#SaveBtn:hover { background: #0D3448; }
            QPushButton#CircuitRow {
                text-align: left;
                height: 40px;
                padding-left: 12px;
                border-radius: 14px;
                background: #0C111B;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 12px;
            }
            QPushButton#CircuitRow:hover { background: #121B2B; }
            QPushButton#CircuitRow[selected="true"] { border: 1px solid #00A6FF; }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        header = GlassCard(self, radius=24)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(18, 14, 16, 14)
        title = QLabel("CIRCUITS")
        title.setObjectName("Title")
        subtitle = QLabel("Create • Edit • Track Settings")
        subtitle.setObjectName("SubTitle")
        hl.addWidget(title)
        hl.addWidget(subtitle)
        root.addWidget(header)

        content = QHBoxLayout()
        content.setSpacing(24)

        form_panel = GlassCard(self, radius=22)
        fl = QVBoxLayout(form_panel)
        fl.setContentsMargins(18, 16, 18, 18)
        fl.setSpacing(10)

        ft = QLabel("Circuit Info")
        ft.setObjectName("SectionTitle")
        fl.addWidget(ft)

        def field(lbl: str, placeholder: str = ""):
            l = QLabel(lbl)
            l.setObjectName("FieldLabel")
            e = QLineEdit()
            if placeholder:
                e.setPlaceholderText(placeholder)
            fl.addWidget(l)
            fl.addWidget(e)
            return e

        name_entry = field("Name", "Es. Monza")
        location_entry = field("Location", "Es. Monza, IT")
        track_len_entry = field("Track Length (m)", "Es. 5793")
        s1_entry = field("Sector 1 (m)", "Es. 1900")
        s2_entry = field("Sector 2 (m)", "Es. 2000")
        s3_entry = field("Sector 3 (m)", "Es. 1893")

        notes_lbl = QLabel("Notes")
        notes_lbl.setObjectName("FieldLabel")
        notes_entry = QTextEdit()
        notes_entry.setMinimumHeight(92)
        fl.addWidget(notes_lbl)
        fl.addWidget(notes_entry)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        reset_btn = QPushButton("Reset")
        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("DeleteBtn")
        save_btn = QPushButton("Create / Update")
        save_btn.setObjectName("SaveBtn")
        actions.addWidget(reset_btn)
        actions.addWidget(delete_btn)
        actions.addWidget(save_btn)
        fl.addLayout(actions)

        hint = QLabel("Tip: la somma S1+S2+S3 dovrebbe essere vicina alla lunghezza pista.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        fl.addWidget(hint)
        fl.addStretch(1)

        list_panel = GlassCard(self, radius=22)
        ll = QVBoxLayout(list_panel)
        ll.setContentsMargins(18, 16, 18, 18)
        ll.setSpacing(10)

        lt = QLabel("Circuits List")
        lt.setObjectName("SectionTitle")
        ll.addWidget(lt)

        search_entry = QLineEdit()
        search_entry.setPlaceholderText("Search by name / location…")
        ll.addWidget(search_entry)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet(
            """
            QScrollArea { background: transparent; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #121B2B; border-radius: 5px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            """
        )

        scroll_frame = QFrame()
        scroll_frame.setStyleSheet(
            """
            QFrame {
                background: #0E1522;
                border: 1px solid #1A2433;
                border-radius: 18px;
            }
            """
        )

        outer = QVBoxLayout(scroll_frame)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setAlignment(Qt.AlignTop)

        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll_layout.addStretch(1)

        outer.addWidget(scroll_container, 0, Qt.AlignTop)
        outer.addStretch(1)

        scroll_area.setWidget(scroll_frame)
        ll.addWidget(scroll_area, 1)

        status_label = QLabel("Ready.")
        status_label.setObjectName("Status")
        ll.addWidget(status_label)

        content.addWidget(form_panel, 1)
        content.addWidget(list_panel, 1)
        root.addLayout(content, 1)

        self.refs = CircuitsWindowUIRefs(
            name_entry=name_entry,
            location_entry=location_entry,
            track_len_entry=track_len_entry,
            s1_entry=s1_entry,
            s2_entry=s2_entry,
            s3_entry=s3_entry,
            notes_entry=notes_entry,
            reset_btn=reset_btn,
            delete_btn=delete_btn,
            save_btn=save_btn,
            search_entry=search_entry,
            scroll_area=scroll_area,
            scroll_container=scroll_container,
            scroll_layout=scroll_layout,
            status_label=status_label,
        )
