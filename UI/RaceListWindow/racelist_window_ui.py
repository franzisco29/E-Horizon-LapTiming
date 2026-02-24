# UI/RaceListWindow/racelist_window_ui.py
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QFrame,
    QScrollArea, QCheckBox
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
class RaceListWindowUIRefs:
    # left builder
    name_edit: QLineEdit
    filter_combo: QComboBox
    select_all_btn: QPushButton
    unselect_all_btn: QPushButton
    available_scroll_area: QScrollArea
    available_container: QWidget
    available_layout: QVBoxLayout
    create_btn: QPushButton
    cancel_btn: QPushButton
    hint_label: QLabel

    # right lists
    lists_scroll_area: QScrollArea
    lists_container: QWidget
    lists_layout: QVBoxLayout
    edit_btn: QPushButton
    delete_btn: QPushButton
    new_btn: QPushButton
    refresh_btn: QPushButton

    status_label: QLabel
    title_label: QLabel


class RaceListWindowUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RaceListWindowUI")
        self.setWindowTitle("E-Horizon • Race Lists")
        self.setMinimumSize(1100, 650)

        self.setStyleSheet("""
            QWidget#RaceListWindowUI {
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
            QLabel#SubTitle { color: #A8B3C7; }
            QLabel#SectionTitle { font-size: 11pt; font-weight: 700; }
            QLabel#Hint, QLabel#Status { color: #7F8AA1; font-size: 9pt; }

            QLineEdit {
                height: 40px;
                border-radius: 14px;
                padding: 0 12px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
            }
            QLineEdit:focus { border: 1px solid #00A6FF; }

            QComboBox {
                height: 38px;
                border-radius: 14px;
                padding: 0 10px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
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
            }
            QPushButton:hover {
                background: #121B2B;
                border: 1px solid rgba(0,166,255,0.65);
            }
            QPushButton#Primary {
                background: #0B2A3A;
                border: 1px solid #00A6FF;
            }
            QPushButton#Danger {
                background: #1A1014;
                border: 1px solid #3A1F2A;
                color: #FFD6DE;
            }
            QPushButton#Danger:hover { background: #24141A; }

            QCheckBox {
                spacing: 10px;
                font-size: 10pt;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 1px solid #1A2433;
                background: #0E1522;
            }
            QCheckBox::indicator:checked {
                background: #00A6FF;
                border: 1px solid #00A6FF;
            }

            QScrollArea { background: transparent; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #121B2B; border-radius: 5px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        # header
        header = GlassCard(self, radius=22)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(18, 16, 18, 16)
        title = QLabel("RACE LISTS")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Create • Edit • Manage session lists (Drivers / Roadsters)")
        subtitle.setObjectName("SubTitle")
        subtitle.setAlignment(Qt.AlignCenter)
        hl.addWidget(title)
        hl.addWidget(subtitle)
        root.addWidget(header)

        content = QHBoxLayout()
        content.setSpacing(24)

        # LEFT builder
        left = GlassCard(self, radius=22)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(18, 16, 18, 18)
        ll.setSpacing(10)

        lt = QLabel("Builder")
        lt.setObjectName("SectionTitle")
        ll.addWidget(lt)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("List name (e.g. Q1_RaceList, Hyperpole_RaceList, Endurance_RaceList)")
        ll.addWidget(name_edit)

        filter_combo = QComboBox()
        filter_combo.addItems(["All Drivers", "AM (Not Pro)", "PRO", "ROADSTERS (Endurance)"])
        ll.addWidget(filter_combo)

        top_actions = QHBoxLayout()
        select_all_btn = QPushButton("Select all")
        unselect_all_btn = QPushButton("Unselect all")
        top_actions.addWidget(select_all_btn)
        top_actions.addWidget(unselect_all_btn)
        ll.addLayout(top_actions)

        # available scroll
        available_scroll_area = QScrollArea()
        available_scroll_area.setWidgetResizable(True)
        available_scroll_area.setFrameShape(QFrame.NoFrame)

        available_frame = QFrame()
        available_frame.setStyleSheet("""
            QFrame {
                background: #0E1522;
                border: 1px solid #1A2433;
                border-radius: 18px;
            }
        """)
        afl = QVBoxLayout(available_frame)
        afl.setContentsMargins(10, 10, 10, 10)

        available_container = QWidget()
        available_layout = QVBoxLayout(available_container)
        available_layout.setContentsMargins(0, 0, 0, 0)
        available_layout.setSpacing(8)
        available_layout.addStretch(1)

        afl.addWidget(available_container)
        available_scroll_area.setWidget(available_frame)
        ll.addWidget(available_scroll_area, 1)

        hint = QLabel("Tip: cambia filtro per passare tra Drivers e Roadsters (Endurance).")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        ll.addWidget(hint)

        bottom_left = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        create_btn = QPushButton("Create / Update")
        create_btn.setObjectName("Primary")
        bottom_left.addWidget(cancel_btn)
        bottom_left.addWidget(create_btn)
        ll.addLayout(bottom_left)

        # RIGHT lists
        right = GlassCard(self, radius=22)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 16, 18, 18)
        rl.setSpacing(10)

        rt = QLabel("Existing lists")
        rt.setObjectName("SectionTitle")
        rl.addWidget(rt)

        right_actions = QHBoxLayout()
        new_btn = QPushButton("New")
        refresh_btn = QPushButton("Refresh")
        edit_btn = QPushButton("Edit selected")
        delete_btn = QPushButton("Delete selected")
        delete_btn.setObjectName("Danger")
        right_actions.addWidget(new_btn)
        right_actions.addWidget(refresh_btn)
        right_actions.addWidget(edit_btn)
        right_actions.addWidget(delete_btn)
        rl.addLayout(right_actions)

        lists_scroll_area = QScrollArea()
        lists_scroll_area.setWidgetResizable(True)
        lists_scroll_area.setFrameShape(QFrame.NoFrame)

        lists_frame = QFrame()
        lists_frame.setStyleSheet("""
            QFrame {
                background: #0E1522;
                border: 1px solid #1A2433;
                border-radius: 18px;
            }
        """)
        lfl = QVBoxLayout(lists_frame)
        lfl.setContentsMargins(10, 10, 10, 10)

        lists_container = QWidget()
        lists_layout = QVBoxLayout(lists_container)
        lists_layout.setContentsMargins(0, 0, 0, 0)
        lists_layout.setSpacing(8)
        lists_layout.addStretch(1)

        lfl.addWidget(lists_container)
        lists_scroll_area.setWidget(lists_frame)
        rl.addWidget(lists_scroll_area, 1)

        status = QLabel("Ready.")
        status.setObjectName("Status")
        rl.addWidget(status)

        content.addWidget(left, 1)
        content.addWidget(right, 1)
        root.addLayout(content, 1)

        self.refs = RaceListWindowUIRefs(
            name_edit=name_edit,
            filter_combo=filter_combo,
            select_all_btn=select_all_btn,
            unselect_all_btn=unselect_all_btn,
            available_scroll_area=available_scroll_area,
            available_container=available_container,
            available_layout=available_layout,
            create_btn=create_btn,
            cancel_btn=cancel_btn,
            hint_label=hint,
            lists_scroll_area=lists_scroll_area,
            lists_container=lists_container,
            lists_layout=lists_layout,
            edit_btn=edit_btn,
            delete_btn=delete_btn,
            new_btn=new_btn,
            refresh_btn=refresh_btn,
            status_label=status,
            title_label=title,
        )