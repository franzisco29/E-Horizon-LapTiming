from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox,
    QComboBox, QFrame, QScrollArea, QSizePolicy, QSpacerItem
)




# --- Helper: "glass card" frame ---
class GlassCard(QFrame):
    def __init__(self, parent=None, radius: int = 22):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self._radius = radius
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame#GlassCard {{
                background: #0C111B;
                border: 1px solid #1A2433;
                border-radius: {radius}px;
            }}
        """)


@dataclass
class DriversWindowUIRefs:
    # Header
    title_label: QLabel
    subtitle_label: QLabel
    settings_btn: QPushButton

    # Form inputs
    name_entry: QLineEdit
    surname_entry: QLineEdit
    team_entry: QLineEdit
    transponder_entry: QLineEdit
    race_number_entry: QLineEdit
    pro_checkbox: QCheckBox

    # Form actions
    reset_btn: QPushButton
    delete_btn: QPushButton
    save_btn: QPushButton
    hint_label: QLabel

    # List controls
    filter_option: QComboBox
    search_entry: QLineEdit
    scroll_container: QWidget
    scroll_layout: QVBoxLayout

    # Nav
    prev_btn: QPushButton
    refresh_btn: QPushButton
    next_btn: QPushButton

    # Status
    status_label: QLabel
    
    scroll_area: QScrollArea


class DriversWindowUI(QWidget):
    """
    Solo UI (layout + stile). La logica la colleghi da drivers_window.py.
    Espone i riferimenti ai widget tramite self.refs
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DriversWindowUI")
        self.setWindowTitle("E-Horizon • Drivers")
        self.setMinimumSize(980, 600)
        self.resize(1100, 650)

        # App background
        self.setStyleSheet("""
            QWidget#DriversWindowUI {
                    background: #070B12;
                    color: #EAF2FF;
                    font-family: "Google Sans";
                }
            QLabel#Title {
                color: #EAF2FF;
                font-size: 28px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#SubTitle {
                color: #A8B3C7;
                font-size: 13px;
            }
            QLabel#SectionTitle {
                color: #EAF2FF;
                font-size: 15px;
                font-weight: 600;
            }
            QLabel#FieldLabel {
                color: #A8B3C7;
                font-size: 12px;
            }
            QLineEdit {
                height: 40px;
                border-radius: 14px;
                padding: 0 12px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #00A6FF;
            }
            QComboBox {
                height: 38px;
                border-radius: 14px;
                padding: 0 10px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
                width: 28px;
            }
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
                font-size: 12px;
            }
            QPushButton:hover {
                background: #121B2B;
            }
            QPushButton#SettingsBtn {
                width: 44px;
                height: 44px;
                font-size: 16px;
            }
            QPushButton#DeleteBtn {
                background: #1A1014;
                border: 1px solid #3A1F2A;
                color: #FFD6DE;
            }
            QPushButton#DeleteBtn:hover {
                background: #24141A;
            }
            QPushButton#SaveBtn {
                background: #0B2A3A;
                border: 1px solid #00A6FF;
                color: #EAF2FF;
            }
            QPushButton#SaveBtn:hover {
                background: #0D3448;
            }
            QCheckBox {
                background: transparent;   /* <-- QUESTA TI MANCA */
                spacing: 10px;
                color: #EAF2FF;
                font-size: 12px;
                font-weight: 600;
            }

            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 6px;
                border: 1px solid #1A2433;
                background: #0E1522;
            }
            QCheckBox::indicator:checked {
                background: #00A6FF;
                border: 1px solid #00A6FF;
            }
            QLabel#Hint {
                color: #7F8AA1;
                font-size: 11px;
            }
            QLabel#Status {
                color: #7F8AA1;
                font-size: 11px;
            }
            
            QPushButton#DriverRow {
                text-align: left;
                height: 40px;
                padding-left: 12px;
                border-radius: 14px;
                background: #0C111B;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 12px;
            }
            QPushButton#DriverRow:hover {
                background: #121B2B;
            }
            QPushButton#DriverRow[selected="true"] {
                border: 1px solid #00A6FF;
            }

        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        # ===== Header card =====
        header = GlassCard(self, radius=24)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 16, 14)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_label = QLabel("DRIVERS")
        title_label.setObjectName("Title")

        subtitle_label = QLabel("Create • Edit • Manage")
        subtitle_label.setObjectName("SubTitle")

        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        title_box.addStretch(1)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("SettingsBtn")
        settings_btn.setFixedSize(44, 44)

        header_layout.addLayout(title_box, 1)
        header_layout.addWidget(settings_btn, 0, Qt.AlignRight | Qt.AlignVCenter)

        root.addWidget(header)

        # ===== Main content: 2 columns =====
        content = QHBoxLayout()
        content.setSpacing(24)

        # LEFT: form panel
        form_panel = GlassCard(self, radius=22)
        form_layout = QVBoxLayout(form_panel)
        form_layout.setContentsMargins(18, 16, 18, 18)
        form_layout.setSpacing(10)

        form_title = QLabel("Driver Info")
        form_title.setObjectName("SectionTitle")
        form_layout.addWidget(form_title)

        def field(label: str):
            lbl = QLabel(label)
            lbl.setObjectName("FieldLabel")
            ent = QLineEdit()
            return lbl, ent

        lbl_name, name_entry = field("Name")
        lbl_surname, surname_entry = field("Surname")
        lbl_team, team_entry = field("Team")
        lbl_transp, transponder_entry = field("Transponder ID (Number)")
        lbl_rnum, race_number_entry = field("Race Number (#)")

        for lbl, ent in [
            (lbl_name, name_entry),
            (lbl_surname, surname_entry),
            (lbl_team, team_entry),
            (lbl_transp, transponder_entry),
            (lbl_rnum, race_number_entry),
        ]:
            form_layout.addWidget(lbl)
            form_layout.addWidget(ent)

        pro_checkbox = QCheckBox("PRO DRIVER")
        form_layout.addWidget(pro_checkbox)

        # actions row
        actions = QHBoxLayout()
        actions.setSpacing(10)

        reset_btn = QPushButton("↺ Reset")
        delete_btn = QPushButton("🗑 Delete")
        delete_btn.setObjectName("DeleteBtn")
        save_btn = QPushButton("✓ Create / Update")
        save_btn.setObjectName("SaveBtn")

        actions.addWidget(reset_btn)
        actions.addWidget(delete_btn)
        actions.addWidget(save_btn)

        form_layout.addLayout(actions)

        hint_label = QLabel("Tip: select a driver on the right to edit, or fill fields to create a new one.")
        hint_label.setObjectName("Hint")
        hint_label.setWordWrap(True)
        form_layout.addWidget(hint_label)
        form_layout.addStretch(1)

        # RIGHT: list panel
        list_panel = GlassCard(self, radius=22)
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(18, 16, 18, 18)
        list_layout.setSpacing(10)

        list_title = QLabel("Drivers List")
        list_title.setObjectName("SectionTitle")
        list_layout.addWidget(list_title)

        top_controls = QHBoxLayout()
        top_controls.setSpacing(10)

        filter_option = QComboBox()
        filter_option.addItems(["All", "AM (Not Pro)", "PRO"])
        filter_option.setFixedWidth(170)

        search_entry = QLineEdit()
        search_entry.setPlaceholderText("Search by name / surname / team…")

        top_controls.addWidget(filter_option)
        top_controls.addWidget(search_entry, 1)

        list_layout.addLayout(top_controls)

        # scroll area for list items
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
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
        

        scroll_frame = QFrame()
        scroll_frame.setStyleSheet("""
            QFrame {
                background: #0E1522;
                border: 1px solid #1A2433;
                border-radius: 18px;
            }
        """)
        scroll_outer = QVBoxLayout(scroll_frame)
        scroll_outer.setContentsMargins(10, 10, 10, 10)

        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)
        scroll_layout.addStretch(1)

        scroll_outer.addWidget(scroll_container)
        scroll_area.setWidget(scroll_frame)

        list_layout.addWidget(scroll_area, 1)

        nav = QHBoxLayout()
        nav.setSpacing(10)
        prev_btn = QPushButton("‹ Prev")
        refresh_btn = QPushButton("⟳ Refresh")
        next_btn = QPushButton("Next ›")
        nav.addWidget(prev_btn)
        nav.addWidget(refresh_btn)
        nav.addWidget(next_btn)
        list_layout.addLayout(nav)
        
        prev_btn.hide()
        next_btn.hide()

        

        status_label = QLabel("Ready.")
        status_label.setObjectName("Status")
        list_layout.addWidget(status_label)

        # Add panels to content
        content.addWidget(form_panel, 1)
        content.addWidget(list_panel, 1)
        root.addLayout(content, 1)

        # Expose references (come facevi con attributi CTk)
        self.refs = DriversWindowUIRefs(
            title_label=title_label,
            subtitle_label=subtitle_label,
            settings_btn=settings_btn,
            name_entry=name_entry,
            surname_entry=surname_entry,
            team_entry=team_entry,
            transponder_entry=transponder_entry,
            race_number_entry=race_number_entry,
            pro_checkbox=pro_checkbox,
            reset_btn=reset_btn,
            delete_btn=delete_btn,
            save_btn=save_btn,
            hint_label=hint_label,
            filter_option=filter_option,
            search_entry=search_entry,
            scroll_container=scroll_container,
            scroll_layout=scroll_layout,
            prev_btn=prev_btn,
            refresh_btn=refresh_btn,
            next_btn=next_btn,
            status_label=status_label,
            scroll_area=scroll_area,
        )
