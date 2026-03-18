# UI/SettingsWindow/settings_window_ui.py
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QComboBox,
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
class SettingsWindowUIRefs:
    debug_check: QCheckBox
    live_check: QCheckBox
    tv_check: QCheckBox
    tv_tower_check: QCheckBox
    monitor_combo: QComboBox
    conn_type_combo: QComboBox
    debounce_edit: QLineEdit
    manual_start_check: QCheckBox

    live_ip_edit: QLineEdit
    live_port_edit: QLineEdit
    live_public_check: QCheckBox
    live_box: QWidget
    starting_box: QWidget

    tcp_box: QWidget
    tcp_ip_value_label: QLabel
    tcp_port_edit: QLineEdit
    dev_checks: list[QCheckBox]
    summary_conn_value: QLabel
    summary_start_value: QLabel
    summary_live_value: QLabel
    summary_profile_value: QLabel

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
        self.setMinimumSize(1080, 640)

        self.setStyleSheet("""
            QWidget#SettingsWindowUI {
                background: #070B12;
                color: #EAF2FF;
                font-family: "Google Sans";
                font-size: 10pt;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }

            QLabel { background: transparent; }

            QLabel#Title {
                font-family: "Audiowide";
                font-size: 18pt;
                letter-spacing: 1px;
            }
            QLabel#SubTitle {
                color: #9FB1CC;
                font-size: 9.5pt;
                font-weight: 500;
            }
            QLabel#GroupTitle {
                font-size: 11pt;
                font-weight: 600;
            }
            QLabel#FieldLabel {
                color: #A8B3C7;
                font-size: 10pt;
            }
            QLabel#ValueLabel {
                color: #EAF2FF;
                font-size: 10pt;
                font-weight: 600;
            }
            QFrame#SectionDivider {
                background: #152033;
                min-height: 1px;
                max-height: 1px;
                border: none;
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
                font-weight: 600;
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
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ===== Header =====
        header = GlassCard(self, radius=22)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(18, 14, 18, 14)
        hl.setSpacing(4)
        title = QLabel("IMPOSTAZIONI")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Configurazione generale, Live Timing e connessioni TCP")
        subtitle.setObjectName("SubTitle")
        subtitle.setAlignment(Qt.AlignCenter)
        hl.addWidget(title)
        hl.addWidget(subtitle)
        root.addWidget(header)

        # ===== Main (2 columns) =====
        content_host = QWidget(self)
        content = QHBoxLayout(content_host)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(18)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content_host)

        root.addWidget(scroll, 1)

        # LEFT column
        left = QVBoxLayout()
        left.setSpacing(14)
        left.setAlignment(Qt.AlignTop)

        # ---- General card ----
        general = GlassCard(self, radius=22)
        gl = QGridLayout(general)
        gl.setContentsMargins(18, 16, 18, 18)
        gl.setHorizontalSpacing(14)
        gl.setVerticalSpacing(12)
        
        gl.setColumnStretch(0, 0)
        gl.setColumnStretch(1, 1)
        gl.setColumnMinimumWidth(0, 170)
                
        gt = QLabel("General Settings")
        gt.setObjectName("GroupTitle")
        gl.addWidget(gt, 0, 0, 1, 2)

        general_divider = QFrame()
        general_divider.setObjectName("SectionDivider")
        gl.addWidget(general_divider, 1, 0, 1, 2)

        debug_check = QCheckBox("Debug")
        live_check = QCheckBox("Live Timing")
        tv_check = QCheckBox("Tv Tower")

        checks_row = QHBoxLayout()
        checks_row.setContentsMargins(0, 0, 0, 0)
        checks_row.setSpacing(10)
        checks_row.addWidget(live_check)
        checks_row.addWidget(debug_check)
        checks_row.addWidget(tv_check)
        checks_row.addStretch(1)

        gl.addLayout(checks_row, 2, 0, 1, 2)

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

        left.addWidget(general)

        # ---- Starting card ----
        starting_box = GlassCard(self, radius=22)
        sl = QGridLayout(starting_box)
        sl.setContentsMargins(18, 16, 18, 18)
        sl.setHorizontalSpacing(12)
        sl.setVerticalSpacing(10)
        sl.setColumnStretch(0, 1)

        st = QLabel("Starting")
        st.setObjectName("GroupTitle")
        sl.addWidget(st, 0, 0)

        starting_divider = QFrame()
        starting_divider.setObjectName("SectionDivider")
        sl.addWidget(starting_divider, 1, 0)

        manual_start_check = QCheckBox("Manual Start")
        manual_start_check.setToolTip("Abilita sequenza manuale di start (comando START_PROC).")
        sl.addWidget(manual_start_check, 2, 0)

        start_hint = QLabel("Se disattivato, lo start passa in automatico senza step manuale.")
        start_hint.setObjectName("FieldLabel")
        start_hint.setWordWrap(True)
        sl.addWidget(start_hint, 3, 0)

        sl.setRowStretch(4, 1)

        left.addWidget(starting_box)

        # ---- LiveTiming card ----
        live_box = GlassCard(self, radius=22)
        ll = QGridLayout(live_box)
        ll.setContentsMargins(18, 16, 18, 18)
        ll.setHorizontalSpacing(12)
        ll.setVerticalSpacing(10)
        ll.setColumnMinimumWidth(0, 170)
        ll.setColumnStretch(1, 1)

        lt = QLabel("LiveTiming")
        lt.setObjectName("GroupTitle")
        ll.addWidget(lt, 0, 0, 1, 2)

        live_divider = QFrame()
        live_divider.setObjectName("SectionDivider")
        ll.addWidget(live_divider, 1, 0, 1, 2)

        lip = QLabel("LIVE IP")
        lip.setObjectName("FieldLabel")
        live_ip_edit = QLineEdit()
        ll.addWidget(lip, 2, 0)
        ll.addWidget(live_ip_edit, 2, 1)

        lpt = QLabel("LIVE Port")
        lpt.setObjectName("FieldLabel")
        live_port_edit = QLineEdit()
        ll.addWidget(lpt, 3, 0)
        ll.addWidget(live_port_edit, 3, 1)

        live_public_check = QCheckBox("Public Tunnel (ngrok)")
        ll.addWidget(live_public_check, 4, 0, 1, 2)

        left.addWidget(live_box)

        # ---- Folder card ----
        folder = GlassCard(self, radius=22)
        fl = QGridLayout(folder)
        fl.setContentsMargins(18, 16, 18, 18)
        fl.setHorizontalSpacing(12)
        fl.setVerticalSpacing(10)
        fl.setColumnMinimumWidth(0, 170)
        fl.setColumnStretch(1, 1)

        ft = QLabel("Folder")
        ft.setObjectName("GroupTitle")
        fl.addWidget(ft, 0, 0, 1, 2)

        folder_divider = QFrame()
        folder_divider.setObjectName("SectionDivider")
        fl.addWidget(folder_divider, 1, 0, 1, 2)

        fp = QLabel("Cartella")
        fp.setObjectName("FieldLabel")
        root_path_edit = QLineEdit()
        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(52)
        browse_btn.setToolTip("Seleziona cartella")

        fl.addWidget(fp, 2, 0)

        hpath = QHBoxLayout()
        hpath.setContentsMargins(0, 0, 0, 0)
        hpath.setSpacing(10)
        hpath.addWidget(root_path_edit, 1)
        hpath.addWidget(browse_btn, 0)

        fl.addLayout(hpath, 2, 1)

        left.addWidget(folder)
        left.addStretch(1)

        # RIGHT column (TCP + summary)
        right = QVBoxLayout()
        right.setSpacing(14)
        right.setAlignment(Qt.AlignTop)

        tcp_card = GlassCard(self, radius=22)
        tr = QGridLayout(tcp_card)
        tr.setContentsMargins(18, 16, 18, 18)
        tr.setHorizontalSpacing(12)
        tr.setVerticalSpacing(12)
        tr.setColumnMinimumWidth(0, 120)
        tr.setColumnStretch(1, 1)

        ttitle = QLabel("TCP Connection")
        ttitle.setObjectName("GroupTitle")
        tr.addWidget(ttitle, 0, 0, 1, 2)

        tcp_divider = QFrame()
        tcp_divider.setObjectName("SectionDivider")
        tr.addWidget(tcp_divider, 1, 0, 1, 2)

        tip = QLabel("APP IP")
        tip.setObjectName("FieldLabel")
        tcp_ip_value_label = QLabel("-")
        tcp_ip_value_label.setObjectName("FieldLabel")
        tr.addWidget(tip, 2, 0)
        tr.addWidget(tcp_ip_value_label, 2, 1, alignment=Qt.AlignLeft)

        tp = QLabel("TCP Port")
        tp.setObjectName("FieldLabel")
        tcp_port_edit = QLineEdit()
        tcp_port_edit.setMaximumWidth(220)
        tr.addWidget(tp, 3, 0)
        tr.addWidget(tcp_port_edit, 3, 1, alignment=Qt.AlignLeft)

        dev_title = QLabel("Dispositivi attivi")
        dev_title.setObjectName("FieldLabel")
        tr.addWidget(dev_title, 4, 0, 1, 2)

        names = ["Centrale", "Settore 1", "Settore 2", "Pit In", "Pit Out", "Semaforo"]
        dev_checks: list[QCheckBox] = []
        devices_grid = QGridLayout()
        devices_grid.setContentsMargins(0, 4, 0, 0)
        devices_grid.setHorizontalSpacing(12)
        devices_grid.setVerticalSpacing(8)

        for i, n in enumerate(names):
            cb = QCheckBox(n)
            dev_checks.append(cb)
            devices_grid.addWidget(cb, i // 2, i % 2)

        tr.addLayout(devices_grid, 5, 0, 1, 2)
        tr.setRowStretch(6, 1)

        summary_card = GlassCard(self, radius=22)
        sr = QGridLayout(summary_card)
        sr.setContentsMargins(18, 16, 18, 18)
        sr.setHorizontalSpacing(12)
        sr.setVerticalSpacing(10)
        sr.setColumnMinimumWidth(0, 160)
        sr.setColumnStretch(1, 1)

        summary_title = QLabel("Stato Rapido")
        summary_title.setObjectName("GroupTitle")
        sr.addWidget(summary_title, 0, 0, 1, 2)

        summary_divider = QFrame()
        summary_divider.setObjectName("SectionDivider")
        sr.addWidget(summary_divider, 1, 0, 1, 2)

        s_conn = QLabel("Comunicazione")
        s_conn.setObjectName("FieldLabel")
        summary_conn_value = QLabel("-")
        summary_conn_value.setObjectName("ValueLabel")
        sr.addWidget(s_conn, 2, 0)
        sr.addWidget(summary_conn_value, 2, 1)

        s_start = QLabel("Modalità Start")
        s_start.setObjectName("FieldLabel")
        summary_start_value = QLabel("-")
        summary_start_value.setObjectName("ValueLabel")
        sr.addWidget(s_start, 3, 0)
        sr.addWidget(summary_start_value, 3, 1)

        s_live = QLabel("Live Timing")
        s_live.setObjectName("FieldLabel")
        summary_live_value = QLabel("-")
        summary_live_value.setObjectName("ValueLabel")
        sr.addWidget(s_live, 4, 0)
        sr.addWidget(summary_live_value, 4, 1)

        s_profile = QLabel("Profilo")
        s_profile.setObjectName("FieldLabel")
        summary_profile_value = QLabel("-")
        summary_profile_value.setObjectName("ValueLabel")
        sr.addWidget(s_profile, 5, 0)
        sr.addWidget(summary_profile_value, 5, 1)

        sr.setRowStretch(6, 1)

        right.addWidget(tcp_card)
        right.addWidget(summary_card)
        right.addStretch(1)

        # Bottom buttons
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.setContentsMargins(0, 4, 0, 0)
        bottom.addStretch(1)
        cancel_btn = QPushButton("Annulla")
        cancel_btn.setMinimumWidth(130)
        save_btn = QPushButton("Salva")
        save_btn.setMinimumWidth(150)
        save_btn.setObjectName("Primary")
        bottom.addWidget(cancel_btn)
        bottom.addWidget(save_btn)

        # Assemble
        content.addLayout(left, 5)
        content.addLayout(right, 4)
        root.addLayout(bottom)

        self.refs = SettingsWindowUIRefs(
            debug_check=debug_check,
            live_check=live_check,
            tv_check=tv_check,
            tv_tower_check=tv_check,
            monitor_combo=monitor_combo,
            conn_type_combo=conn_type_combo,
            debounce_edit=debounce_edit,
            manual_start_check=manual_start_check,
            live_ip_edit=live_ip_edit,
            live_port_edit=live_port_edit,
            live_public_check=live_public_check,
            live_box=live_box,
            starting_box=starting_box,
            tcp_box=tcp_card,
            tcp_ip_value_label=tcp_ip_value_label,
            tcp_port_edit=tcp_port_edit,
            dev_checks=dev_checks,
            summary_conn_value=summary_conn_value,
            summary_start_value=summary_start_value,
            summary_live_value=summary_live_value,
            summary_profile_value=summary_profile_value,
            root_path_edit=root_path_edit,
            browse_btn=browse_btn,
            cancel_btn=cancel_btn,
            save_btn=save_btn,
            title_label=title,
        )
