from __future__ import annotations
from dataclasses import dataclass
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QComboBox, QFrame,
    QSizePolicy, QTableWidget, QSpacerItem
)

@dataclass(slots=True)
class RaceManagerWindowRefs:
    timer_value: QLabel
    session_value: QLabel
    pit_label: QLabel
    track_value: QLabel
    track_panel: QFrame
    ip_value: QLabel
    racelist_box: QComboBox
    session_box: QComboBox
    load_btn: QPushButton
    start_btn: QPushButton
    reset_btn: QPushButton
    save_results_btn: QPushButton
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
    lap_table: QTableWidget

def _btn(text: str, min_w: int = 0) -> QPushButton:
    b = QPushButton(text)
    if min_w:
        b.setMinimumWidth(min_w)
    b.setCursor(Qt.PointingHandCursor)
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
            margin-top: 10px;
            padding: 10px;
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
            padding: 4px 8px;
            min-height: 20px;
        }
        QPushButton:hover { background: rgba(255,255,255,0.15); }
        QTableWidget { background: #232629; border-radius: 4px; }
        QLabel { color: rgba(233,238,245,0.92); }
    """)

    main_layout = QVBoxLayout(root)
    top_layout = QHBoxLayout()

    # --- SESSION INFO ---
    gb_info = QGroupBox("Session Info")
    gl_info = QGridLayout(gb_info)
    gl_info.setVerticalSpacing(14)
    gl_info.setContentsMargins(10, 10, 10, 10)
    
    timer_val = QLabel("00:00")
    session_val = QLabel("Practice")
    pit_val = QLabel("Pit Closed")
    track_val = QLabel("—")
    track_panel = QFrame()
    track_panel.setFixedSize(60, 60)
    track_panel.setStyleSheet("background: #333; border-radius: 5px;")

    gl_info.addWidget(QLabel("Tempo:"), 0, 0)
    gl_info.addWidget(timer_val, 0, 1)
    gl_info.addWidget(QLabel("Sessione:"), 1, 0)
    gl_info.addWidget(session_val, 1, 1)
    gl_info.addWidget(QLabel("Pit:"), 2, 0)
    gl_info.addWidget(pit_val, 2, 1)
    gl_info.addWidget(track_panel, 0, 2, 3, 1)
    
    gl_info.addWidget(QLabel("Track:"), 3, 0)
    gl_info.addWidget(track_val, 3, 1)
    gl_info.addWidget(track_panel, 0, 2, 4, 1)  # <- diventa 4 righe

    # --- DIRECTION CONTROL ---
    gb_dir = QGroupBox("Direction Control")
    gl_dir = QGridLayout(gb_dir)
    gl_dir.setHorizontalSpacing(18)

    # Spaziature: più aria tra righe e tra colonne
    gl_dir.setContentsMargins(12, 18, 12, 14)
    gl_dir.setVerticalSpacing(25)     # <-- più spazio verticale tra righe

    # Colonne: diamo regole chiare
    # 0 label, 1 campo principale (stretch), 2 btn, 3 label, 4 combo, 5 btn
    gl_dir.setColumnMinimumWidth(0, 42)
    gl_dir.setColumnStretch(1, 1)         # combo/lista prende spazio
    gl_dir.setColumnMinimumWidth(2, 86)   # debug
    gl_dir.setColumnMinimumWidth(3, 70)   # "Pre Gara:", "Set State:"
    gl_dir.setColumnMinimumWidth(4, 110)  # combo minutes / status
    gl_dir.setColumnMinimumWidth(5, 100)  # bottoni a destra

    # Riga minima (anti-collasso)
    for r in range(4):
        gl_dir.setRowMinimumHeight(r, 30)

    ip_lbl = QLabel("IP:")
    ip_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    ip_val = QLabel("NONE")
    ip_val.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

    debug_btn = _btn("Debug", 90)

    pre_lbl = QLabel("Pre Gara:")
    pre_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    pre_minutes = QComboBox()
    pre_minutes.addItems(["1", "2", "3", "5", "10"])
    pre_minutes.setMinimumWidth(110)
    pre_btn = _btn("Start", 90)

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

    state_lbl = QLabel("Set State:")
    state_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
    status_box = QComboBox()
    status_box.addItems([ "DNF", "DSQ","DNS"])
    status_box.setMinimumWidth(110)
    apply_status_btn = _btn("Set State", 90)

    # ✅ Riga 0: IP | Debug | Pre Gara
    gl_dir.addWidget(ip_lbl,      0, 0, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(ip_val,      0, 1, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(debug_btn,   0, 2, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(pre_lbl,     0, 3, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(pre_minutes, 0, 4, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(pre_btn,     0, 5, alignment=Qt.AlignVCenter)

    # ✅ Riga 1: Lista | Carica
    gl_dir.addWidget(list_lbl,     1, 0, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(racelist_box, 1, 1, 1, 4)  # spanning
    gl_dir.addWidget(load_btn,     1, 5, alignment=Qt.AlignVCenter)

    # ✅ Riga 2: Sessione | Start Reset Generate (allineati)
    gl_dir.addWidget(sess_lbl,     2, 0, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(session_box,  2, 1, 1, 2)  # spanning per dare aria
    gl_dir.addWidget(start_btn,    2, 3, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(reset_btn,    2, 4, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(save_btn,     2, 5, alignment=Qt.AlignVCenter)

    # ✅ Riga 3: Set State | combo | bottone
    gl_dir.addWidget(state_lbl,        3, 3, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(status_box,       3, 4, alignment=Qt.AlignVCenter)
    gl_dir.addWidget(apply_status_btn, 3, 5, alignment=Qt.AlignVCenter)

    # --- FLAG CONTROL ---
    gb_flag = QGroupBox("Flag Control")
    gl_flag = QGridLayout(gb_flag)
    gl_flag.setContentsMargins(10, 16, 10, 12)
    gl_flag.setVerticalSpacing(14)
    gl_flag.setHorizontalSpacing(12)
    
    flags = {
        "YS1": (0,0), "YS2": (0,1), "YS3": (0,2), "SC": (0,3), "F Lap": (0,4), "OP Pit": (0,5),
        "Green": (1,0), "Red": (1,1), "Clear": (1,2), "VSC": (1,3), "Wet R": (1,4), "CL Pit": (1,5)
    }
    btns = {}
    for text, pos in flags.items():
        btn = _btn(text, 65)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        gl_flag.addWidget(btn, pos[0], pos[1])
        btns[text] = btn

    # --- IMPOSTAZIONI ALTEZZA E POLICY ---
    # Invece di fixed height, usiamo minimum height
    gb_info.setMinimumHeight(200)
    gb_dir.setMinimumHeight(200)
    gb_flag.setMinimumHeight(200)
    
    # Impedisce ai box di crescere verticalmente all'infinito
    gb_info.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    gb_dir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    gb_flag.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    top_layout.addWidget(gb_info)
    top_layout.addWidget(gb_dir, 2)
    top_layout.addWidget(gb_flag)
    
    main_layout.addLayout(top_layout)

    # Padding prima della tabella
    main_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

    # --- TABLE ---
    table = QTableWidget(0, 13)
    table.setHorizontalHeaderLabels(["Pos", "Pilota", "Team", "S1", "S2", "S3", "Last", "Laps", "Status", "Gap", "Int", "Best", "Time"])
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    main_layout.addWidget(table)

    refs = RaceManagerWindowRefs(
        timer_value           = timer_val,
        session_value         = session_val,
        pit_label             = pit_val,
        track_value           = track_val,
        track_panel           = track_panel,
        ip_value              = ip_val,

        racelist_box          = racelist_box,
        session_box           = session_box,
        load_btn              = load_btn,
        start_btn             = start_btn,
        reset_btn             = reset_btn,
        save_results_btn      = save_btn,
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

        lap_table             = table,
    )
    return root, refs