from __future__ import annotations
from dataclasses import dataclass
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QComboBox,
    QSizePolicy, QTableWidget, QSpacerItem
)

@dataclass(slots=True)
class RaceManagerWindowRefs:
    timer_value: QLabel
    sc_time_value: QLabel
    session_value: QLabel
    pit_label: QLabel
    track_value: QLabel
    ip_label: QLabel
    racelist_box: QComboBox
    session_box: QComboBox
    load_btn: QPushButton
    start_btn: QPushButton
    reset_btn: QPushButton
    save_results_btn: QPushButton
    analytics_btn: QPushButton
    live_btn: QPushButton
    live_status_lbl: QLabel
    debug_btn: QPushButton
    pre_race_minutes_box: QComboBox
    pre_race_btn: QPushButton
    status_box: QComboBox
    apply_status_btn: QPushButton
    ys1_btn: QPushButton
    ys2_btn: QPushButton
    ys3_btn: QPushButton
    sc_btn: QPushButton
    vsc_btn: QPushButton
    green_btn: QPushButton
    red_btn: QPushButton
    clear_btn: QPushButton
    wet_btn: QPushButton
    formation_btn: QPushButton
    op_pit_btn: QPushButton
    cl_pit_btn: QPushButton
    flag_group: QGroupBox
    lap_table: QTableWidget

def _btn(text: str, min_w: int = 0) -> QPushButton:
    b = QPushButton(text)
    if min_w:
        b.setMinimumWidth(min_w)
    b.setCursor(Qt.PointingHandCursor)
    return b

def _checkable_btn(text: str, min_w: int = 0) -> QPushButton:
    """Create a checkable button for flag toggle states"""
    b = QPushButton(text)
    if min_w:
        b.setMinimumWidth(min_w)
    b.setCursor(Qt.PointingHandCursor)
    b.setCheckable(True)
    return b

def build_race_manager_ui(parent: QWidget) -> tuple[QWidget, RaceManagerWindowRefs]:
    root = QWidget(parent)
    root.setObjectName("RaceManagerRoot")
    
    # CSS migliorato
    root.setStyleSheet("""
        QWidget#RaceManagerRoot {
            background: #1a1c1f;
            color: #e9eef5;
            font-size: 12px;
        }
        QGroupBox {
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            margin-top: 8px;
            padding: 8px;
            background: rgba(255,255,255,0.02);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QComboBox, QPushButton {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 4px;
            padding: 3px 7px;
            min-height: 18px;
        }
        QPushButton:hover { background: rgba(255,255,255,0.15); }
        QTableWidget { background: #232629; border-radius: 4px; }
        QLabel { color: rgba(233,238,245,0.92); }
    """)

    main_layout = QVBoxLayout(root)
    main_layout.setSpacing(6)
    top_layout = QHBoxLayout()
    top_layout.setSpacing(8)

    # --- SESSION INFO ---
    gb_info = QGroupBox("Session Info")
    gl_info = QGridLayout(gb_info)
    gl_info.setVerticalSpacing(6)
    gl_info.setContentsMargins(8, 8, 8, 8)
    
    timer_val = QLabel("00:00")
    sc_time_val = QLabel("00:00")
    session_val = QLabel("Practice")
    pit_val = QLabel("Pit Closed")
    track_val = QLabel("—")

    gl_info.addWidget(QLabel("Tempo:"), 0, 0)
    gl_info.addWidget(timer_val, 0, 1)
    gl_info.addWidget(QLabel("SC Tempo:"), 1, 0)
    gl_info.addWidget(sc_time_val, 1, 1)
    gl_info.addWidget(QLabel("Sessione:"), 2, 0)
    gl_info.addWidget(session_val, 2, 1)
    gl_info.addWidget(QLabel("Pit:"), 3, 0)
    gl_info.addWidget(pit_val, 3, 1)
    gl_info.addWidget(QLabel("Track:"), 4, 0)
    gl_info.addWidget(track_val, 4, 1)

    # --- DIRECTION CONTROL ---
    gb_dir = QGroupBox("Direction Control")
    dir_layout = QVBoxLayout(gb_dir)
    dir_layout.setContentsMargins(8, 8, 8, 8)
    dir_layout.setSpacing(6)

    ip_lbl = QLabel("IP:")
    ip_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    ip_val = QLabel("NONE")
    ip_val.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

    live_btn = _btn("Live", 74)
    live_status_lbl = QLabel("Privata")
    live_status_lbl.setMinimumWidth(60)
    live_status_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    debug_btn = _btn("Debug", 92)

    pre_lbl = QLabel("Pre Gara:")
    pre_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    pre_minutes = QComboBox()
    pre_minutes.addItems(["1", "2", "3", "5", "10"])
    pre_minutes.setMinimumWidth(110)
    pre_btn = _btn("Start Pre", 110)

    list_lbl = QLabel("Lista:")
    list_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    racelist_box = QComboBox()
    racelist_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    load_btn = _btn("Carica", 90)

    sess_lbl = QLabel("Sess:")
    sess_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    session_box = QComboBox()
    session_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    start_btn = _btn("Start", 90)
    reset_btn = _btn("Reset", 90)
    save_btn = _btn("Generate Result", 130)
    analytics_btn = _btn("Generate Analytics", 140)

    state_lbl = QLabel("Set State:")
    state_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    status_box = QComboBox()
    status_box.addItems(["DNF", "DSQ", "DNS"])
    status_box.setMinimumWidth(110)
    apply_status_btn = _btn("Set State", 90)

    # Sotto-groupbox 1: strumenti e pre-gara
    gb_dir_service = QGroupBox("Service")
    gl_dir_service = QGridLayout(gb_dir_service)
    gl_dir_service.setContentsMargins(8, 8, 8, 8)
    gl_dir_service.setHorizontalSpacing(10)
    gl_dir_service.setVerticalSpacing(6)
    gl_dir_service.setColumnStretch(1, 1)
    gl_dir_service.setRowMinimumHeight(0, 30)

    top_btns = QWidget(gb_dir_service)
    top_btns_lay = QHBoxLayout(top_btns)
    top_btns_lay.setContentsMargins(0, 0, 0, 0)
    top_btns_lay.setSpacing(8)
    top_btns_lay.addWidget(live_btn)
    top_btns_lay.addWidget(live_status_lbl)
    top_btns_lay.addWidget(debug_btn)

    gl_dir_service.addWidget(ip_lbl,      0, 0, alignment=Qt.AlignVCenter)
    gl_dir_service.addWidget(ip_val,      0, 1, alignment=Qt.AlignVCenter)
    gl_dir_service.addWidget(top_btns,    0, 2, alignment=Qt.AlignVCenter)
    gl_dir_service.addWidget(pre_lbl,     0, 3, alignment=Qt.AlignVCenter)
    gl_dir_service.addWidget(pre_minutes, 0, 4, alignment=Qt.AlignVCenter)
    gl_dir_service.addWidget(pre_btn,     0, 5, alignment=Qt.AlignVCenter)

    # Sotto-groupbox 2: sessione/lista/stato
    gb_dir_session = QGroupBox("Session")
    gl_dir_session = QGridLayout(gb_dir_session)
    gl_dir_session.setContentsMargins(8, 8, 8, 8)
    gl_dir_session.setHorizontalSpacing(10)
    gl_dir_session.setVerticalSpacing(6)
    gl_dir_session.setColumnStretch(1, 1)
    gl_dir_session.setRowMinimumHeight(0, 30)
    gl_dir_session.setRowMinimumHeight(1, 30)
    gl_dir_session.setRowMinimumHeight(2, 30)

    gl_dir_session.addWidget(list_lbl,     0, 0, alignment=Qt.AlignVCenter)
    gl_dir_session.addWidget(racelist_box, 0, 1, 1, 4)
    gl_dir_session.addWidget(load_btn,     0, 5, alignment=Qt.AlignVCenter)

    gl_dir_session.addWidget(sess_lbl,     1, 0, alignment=Qt.AlignVCenter)
    gl_dir_session.addWidget(session_box,  1, 1, 1, 2)
    gl_dir_session.addWidget(start_btn,    1, 3, alignment=Qt.AlignVCenter)
    gl_dir_session.addWidget(reset_btn,    1, 4, alignment=Qt.AlignVCenter)
    gl_dir_session.addWidget(save_btn,     1, 5, alignment=Qt.AlignVCenter)

    gl_dir_session.addWidget(state_lbl,         2, 3, alignment=Qt.AlignVCenter)
    gl_dir_session.addWidget(status_box,        2, 4, alignment=Qt.AlignVCenter)
    gl_dir_session.addWidget(apply_status_btn,  2, 5, alignment=Qt.AlignVCenter)
    gl_dir_session.addWidget(analytics_btn,     2, 0, 1, 2, alignment=Qt.AlignVCenter)

    dir_layout.addWidget(gb_dir_service)
    dir_layout.addWidget(gb_dir_session)

    # --- FLAG CONTROL ---
    gb_flag = QGroupBox("Flag Control")
    gl_flag = QGridLayout(gb_flag)
    gl_flag.setContentsMargins(6, 8, 6, 8)
    gl_flag.setVerticalSpacing(6)
    gl_flag.setHorizontalSpacing(6)
    
    flags = {
        "YS1": (0, 0), "YS2": (0, 1), "YS3": (0, 2),
        "SC": (1, 0), "VSC": (1, 1), "F Lap": (1, 2),
        "Green": (2, 0), "Red": (2, 1), "Clear": (2, 2),
        "Wet R": (3, 0), "OP Pit": (3, 1), "CL Pit": (3, 2),
    }
    # Buttons that should be checkable (toggle state)
    checkable_flags = {"YS1", "YS2", "YS3", "Red", "Green"}
    
    btns = {}
    for text, pos in flags.items():
        if text in checkable_flags:
            btn = _checkable_btn(text, 54)
        else:
            btn = _btn(text, 54)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        gl_flag.addWidget(btn, pos[0], pos[1])
        btns[text] = btn

    # --- IMPOSTAZIONI ALTEZZA E POLICY ---
    # Invece di fixed height, usiamo minimum height
    gb_info.setMinimumHeight(0)
    gb_dir.setMinimumHeight(0)
    gb_flag.setMinimumHeight(0)
    gb_info.setMaximumWidth(260)
    gb_flag.setMaximumWidth(360)
    
    # Impedisce ai box di crescere verticalmente all'infinito
    gb_info.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    gb_dir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    gb_flag.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    top_layout.addWidget(gb_info, 1)
    top_layout.addWidget(gb_dir, 3)
    top_layout.addWidget(gb_flag, 1)
    
    main_layout.addLayout(top_layout)

    # Padding prima della tabella
    main_layout.addSpacerItem(QSpacerItem(0, 4, QSizePolicy.Minimum, QSizePolicy.Fixed))

    # --- TABLE ---
    table = QTableWidget(0, 13)
    table.setHorizontalHeaderLabels(["Pos", "Pilota", "Team", "S1", "S2", "S3", "Last", "Laps", "Status", "Gap", "Int", "Best", "Time"])
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    main_layout.addWidget(table)

    refs = RaceManagerWindowRefs(
        timer_value           = timer_val,
        sc_time_value         = sc_time_val,
        session_value         = session_val,
        pit_label             = pit_val,
        track_value           = track_val,
        ip_label              = ip_val,
        racelist_box          = racelist_box,
        session_box           = session_box,
        load_btn              = load_btn,
        start_btn             = start_btn,
        reset_btn             = reset_btn,
        save_results_btn      = save_btn,
        analytics_btn         = analytics_btn,
        live_btn              = live_btn,
        live_status_lbl       = live_status_lbl,
        debug_btn             = debug_btn,
        pre_race_minutes_box  = pre_minutes,
        pre_race_btn          = pre_btn,
        status_box            = status_box,
        apply_status_btn      = apply_status_btn,
        ys1_btn               = btns["YS1"],
        ys2_btn               = btns["YS2"],
        ys3_btn               = btns["YS3"],
        sc_btn                = btns["SC"],
        vsc_btn               = btns["VSC"],
        green_btn             = btns["Green"],
        red_btn               = btns["Red"],
        clear_btn             = btns["Clear"],
        wet_btn               = btns["Wet R"],
        formation_btn         = btns["F Lap"],
        op_pit_btn            = btns["OP Pit"],
        cl_pit_btn            = btns["CL Pit"],
        flag_group            = gb_flag,
        lap_table             = table,
    )
    return root, refs