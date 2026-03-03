# UI/SettingsWindow/settings_window_ui.py
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QComboBox,
    QFrame
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
class SettingsWindowUIRefs:
    debug_check: QCheckBox
    live_check: QCheckBox
    tv_check: QCheckBox
    tv_tower_check: QCheckBox
    monitor_combo: QComboBox
    conn_type_combo: QComboBox
    debounce_edit: QLineEdit

    live_ip_edit: QLineEdit
    live_port_edit: QLineEdit
    live_box: QWidget

    tcp_box: QWidget
    tcp_port_edit: QLineEdit
    dev_checks: list[QCheckBox]

    root_path_edit: QLineEdit
    browse_btn: QPushButton

    cancel_btn: QPushButton
    save_btn: QPushButton

    title_label: QLabel


class SettingsWindowUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsWindowUI")
        self.setWindowTitle("E-Horizon • Settings")
        self.setMinimumSize(1200, 680)

        self.setStyleSheet("""
            QWidget#SettingsWindowUI {
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
            QLabel#GroupTitle {
                font-size: 11pt;
                font-weight: 600;
            }
            QLabel#FieldLabel {
                color: #A8B3C7;
                font-size: 10pt;
            }

            QLineEdit {
                height: 38px;
                border-radius: 14px;
                padding: 0 12px;
                background: #0E1522;
                border: 1px solid #1A2433;
                color: #EAF2FF;
                font-size: 10pt;
            }
            QLineEdit:focus { border: 1px solid #00A6FF; }

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

            /* checkbox: niente “nero dietro” e niente testo tagliato */
            QCheckBox {
                spacing: 10px;
                color: #EAF2FF;
                font-size: 10pt;
                font-weight: 600;
                padding: 6px 8px;
                border-radius: 12px;
                min-height: 30px;
                background: transparent;
            }
            QCheckBox:hover { background: rgba(255,255,255,0.04); }
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
            }
            QPushButton#Primary:hover { background: #0D3448; }

            /* disabled: visibile */
            QLineEdit:disabled, QComboBox:disabled {
                background: #0A0F18;
                border: 1px solid #121A28;
                color: rgba(234,242,255,0.35);
            }
            QCheckBox:disabled { color: rgba(234,242,255,0.35); }
            QCheckBox::indicator:disabled {
                background: #0A0F18;
                border: 1px solid #121A28;
            }
            
            QFrame#GlassCard:disabled {
                background: #0A0F18;
                border: 1px solid rgba(255,255,255,0.06);
            }
            
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        # ===== Header =====
        header = GlassCard(self, radius=22)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(18, 16, 18, 16)
        title = QLabel("IMPOSTAZIONI")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        hl.addWidget(title)
        root.addWidget(header)

        # ===== Main (2 columns) =====
        content = QHBoxLayout()
        content.setSpacing(24)

        # LEFT column
        left = QVBoxLayout()
        left.setSpacing(12)
        left.setAlignment(Qt.AlignTop)  # FIX: no compression madness

        # ---- General card ----
        general = GlassCard(self, radius=22)
        gl = QGridLayout(general)
        gl.setContentsMargins(18, 16, 18, 18)
        gl.setHorizontalSpacing(14)
        gl.setVerticalSpacing(10)
        
        gl.setColumnStretch(0, 0)   # label colonna stretta
        gl.setColumnStretch(1, 1)   # campi colonna espande
        gl.setColumnMinimumWidth(0, 150)  # labels consistenti
                
        gt = QLabel("General Settings")
        gt.setObjectName("GroupTitle")
        gl.addWidget(gt, 0, 0, 1, 2)

        debug_check = QCheckBox("Debug")
        live_check = QCheckBox("Live Timing")
        tv_check = QCheckBox("Tv Tower")

        # place LiveTiming to the left of Debug (side-by-side)
        gl.addWidget(live_check, 1, 0)
        gl.addWidget(debug_check, 1, 1)
        # Tv Tower on next row, spanning both columns
        gl.addWidget(tv_check, 2, 0, 1, 2)

        lab_mon = QLabel("Monitor Out")
        lab_mon.setObjectName("FieldLabel")
        monitor_combo = QComboBox()
        gl.addWidget(lab_mon, 3, 0)
        gl.addWidget(monitor_combo, 3, 1)

        lab_comm = QLabel("Comunicazione")
        lab_comm.setObjectName("FieldLabel")
        conn_type_combo = QComboBox()
        conn_type_combo.addItems(["NONE", "TCP", "SERIAL", "WIFIUDP"])
        gl.addWidget(lab_comm, 4, 0)
        gl.addWidget(conn_type_combo, 4, 1)

        lab_db = QLabel("DeBounce Time (ms)")
        lab_db.setObjectName("FieldLabel")
        debounce_edit = QLineEdit()
        gl.addWidget(lab_db, 5, 0)
        gl.addWidget(debounce_edit, 5, 1)

        gl.setRowStretch(6, 1)

        monitor_combo.setMinimumWidth(260)
        conn_type_combo.setMinimumWidth(260)
        debounce_edit.setMinimumWidth(260)

        left.addWidget(general)

        # ---- LiveTiming card ----
        live_box = GlassCard(self, radius=22)
        ll = QGridLayout(live_box)
        ll.setContentsMargins(18, 16, 18, 18)
        ll.setHorizontalSpacing(12)
        ll.setVerticalSpacing(10)
        ll.setColumnStretch(1, 1)

        lt = QLabel("LiveTiming")
        lt.setObjectName("GroupTitle")
        ll.addWidget(lt, 0, 0, 1, 2)

        lip = QLabel("LIVE IP")
        lip.setObjectName("FieldLabel")
        live_ip_edit = QLineEdit()
        ll.addWidget(lip, 1, 0)
        ll.addWidget(live_ip_edit, 1, 1)

        lpt = QLabel("LIVE Port")
        lpt.setObjectName("FieldLabel")
        live_port_edit = QLineEdit()
        ll.addWidget(lpt, 2, 0)
        ll.addWidget(live_port_edit, 2, 1)
        
        live_ip_edit.setMinimumWidth(260)
        live_port_edit.setMinimumWidth(260)


        left.addWidget(live_box)

        # ---- Folder card ----
        folder = GlassCard(self, radius=22)
        fl = QGridLayout(folder)
        fl.setContentsMargins(18, 16, 18, 18)
        fl.setHorizontalSpacing(12)
        fl.setVerticalSpacing(10)
        fl.setColumnStretch(1, 1)

        ft = QLabel("Folder")
        ft.setObjectName("GroupTitle")
        fl.addWidget(ft, 0, 0, 1, 2)

        fp = QLabel("Cartella")
        fp.setObjectName("FieldLabel")
        root_path_edit = QLineEdit()
        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(44)

        fl.addWidget(fp, 1, 0)

        hpath = QHBoxLayout()
        hpath.setContentsMargins(0, 0, 0, 0)
        hpath.setSpacing(10)
        hpath.addWidget(root_path_edit, 1)
        hpath.addWidget(browse_btn, 0)

        hpath_host = QWidget()
        hpath_host.setLayout(hpath)
        fl.addWidget(hpath_host, 1, 1)

        left.addWidget(folder)
        left.addStretch(1)

        # RIGHT column (TCP)
        tcp_card = GlassCard(self, radius=22)
        tr = QGridLayout(tcp_card)
        tr.setContentsMargins(18, 16, 18, 18)
        tr.setHorizontalSpacing(12)
        tr.setVerticalSpacing(10)
        tr.setColumnStretch(1, 1)

        ttitle = QLabel("TCP Connection")
        ttitle.setObjectName("GroupTitle")
        tr.addWidget(ttitle, 0, 0, 1, 2)

        tp = QLabel("TCP Port")
        tp.setObjectName("FieldLabel")
        tcp_port_edit = QLineEdit()
        tcp_port_edit.setFixedWidth(140)
        tr.addWidget(tp, 1, 0)
        tr.addWidget(tcp_port_edit, 1, 1, alignment=Qt.AlignLeft)

        names = ["Centrale", "Settore 1", "Settore 2", "Pit In", "Pit Out", "Semaforo"]
        dev_checks: list[QCheckBox] = []
        row = 2
        for n in names:
            cb = QCheckBox(n)
            dev_checks.append(cb)
            tr.addWidget(cb, row, 0, 1, 2)
            row += 1

        tr.setRowStretch(row, 1)

        # Bottom buttons
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        cancel_btn = QPushButton("Annulla")
        save_btn = QPushButton("Salva")
        save_btn.setObjectName("Primary")
        bottom.addWidget(cancel_btn)
        bottom.addWidget(save_btn)

        # Assemble
        content.addLayout(left, 1)
        content.addWidget(tcp_card, 1)
        root.addLayout(content, 1)
        root.addLayout(bottom)

        self.refs = SettingsWindowUIRefs(
            debug_check=debug_check,
            live_check=live_check,
            tv_check=tv_check,
            tv_tower_check=tv_check,
            monitor_combo=monitor_combo,
            conn_type_combo=conn_type_combo,
            debounce_edit=debounce_edit,
            live_ip_edit=live_ip_edit,
            live_port_edit=live_port_edit,
            live_box=live_box,
            tcp_box=tcp_card,
            tcp_port_edit=tcp_port_edit,
            dev_checks=dev_checks,
            root_path_edit=root_path_edit,
            browse_btn=browse_btn,
            cancel_btn=cancel_btn,
            save_btn=save_btn,
            title_label=title,
        )
