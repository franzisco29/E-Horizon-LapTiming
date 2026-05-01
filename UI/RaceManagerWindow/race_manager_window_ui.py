from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(slots=True)
class RaceManagerWindowRefs:
    timer_value: QLabel
    sc_time_value: QLabel
    session_value: QLabel
    pit_label: QLabel
    ip_label: QLabel
    device_btn: QToolButton
    recovery_btn: QPushButton
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


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _btn(text: str, min_w: int = 0) -> QPushButton:
    b = QPushButton(text)
    if min_w:
        b.setMinimumWidth(min_w)
    b.setCursor(Qt.PointingHandCursor)
    return b


def _checkable_btn(text: str, min_w: int = 0) -> QPushButton:
    b = QPushButton(text)
    if min_w:
        b.setMinimumWidth(min_w)
    b.setCursor(Qt.PointingHandCursor)
    b.setCheckable(True)
    return b


class _StartButton(QPushButton):
    """Bottone Start che aggiunge automaticamente l'icona coerente col testo.

    Il backend chiama semplicemente ``setText("Stop")`` / ``setText("Resume")``
    ecc. — questa classe antepone l'emoji giusta senza bisogno di modifiche
    al codice chiamante.

    Mapping:
        stop          → ⏹
        sequenza luci → ●
        lights out    → 🏁
        tutto il resto → ▶  (play/avanti/resume/start session/…)
    """

    _MAP: list[tuple[str, str]] = [
        ("stop",     "⏹"),
        ("sequenza", "●"),
        ("lights",   "🏁"),
    ]
    _DEFAULT = "▶"

    def setText(self, text: str) -> None:
        lc = text.lower().strip()
        icon = self._DEFAULT
        for key, ic in self._MAP:
            if key in lc:
                icon = ic
                break
        super().setText(f"{icon}  {text}")


def _vline() -> QFrame:
    """Thin vertical separator matching the dark theme."""
    f = QFrame()
    f.setFrameShape(QFrame.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet("background: rgba(255,255,255,0.08); border: none;")
    return f


# ─────────────────────────────────────────────────────────────────────────────
# Main build function
# ─────────────────────────────────────────────────────────────────────────────

def build_race_manager_ui(parent: QWidget) -> tuple[QWidget, RaceManagerWindowRefs]:
    root = QWidget(parent)
    root.setObjectName("RaceManagerRoot")

    # ── Stylesheet (palette identica alla Home window) ────────────────────────
    root.setStyleSheet("""
        /* ── Root ───────────────────────────────────────────────────── */
        QWidget#RaceManagerRoot {
            background: #060A12;
            color: rgba(255,255,255,0.92);
            font-family: "Google Sans", "Segoe UI", sans-serif;
            font-size: 12px;
        }
        QLabel { background: transparent; }

        /* ── Panel card (glass) ─────────────────────────────────────── */
        QFrame#Panel {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 rgba(255,255,255,0.07),
                stop:1 rgba(255,255,255,0.03));
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 16px;
        }

        /* ── Flag groupbox (usa QGroupBox per .setTitle()) ───────────── */
        QGroupBox#FlagGroup {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 rgba(255,255,255,0.07),
                stop:1 rgba(255,255,255,0.03));
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 16px;
            margin-top: 0px;
            padding: 26px 12px 10px 12px;
            font-size: 10px;
            color: rgba(43,183,255,0.70);
            font-weight: 700;
            letter-spacing: 1px;
        }
        QGroupBox#FlagGroup::title {
            subcontrol-origin: padding;
            subcontrol-position: top left;
            left: 12px;
            top: 6px;
            padding: 0 4px;
        }

        /* ── Labels ─────────────────────────────────────────────────── */
        QLabel#PanelTitle {
            color: rgba(43,183,255,0.70);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
        }
        QLabel#InfoKey {
            color: rgba(255,255,255,0.38);
            font-size: 10px;
            font-weight: 500;
        }
        QLabel#InfoValue {
            color: rgba(255,255,255,0.95);
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#LiveBadge {
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 10px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: 700;
            background: rgba(255,255,255,0.04);
            color: rgba(255,255,255,0.40);
        }

        /* ── Standard inputs ────────────────────────────────────────── */
        QComboBox, QPushButton {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.11);
            border-radius: 8px;
            padding: 3px 10px;
            min-height: 24px;
            color: rgba(255,255,255,0.88);
            font-size: 11px;
        }
        QComboBox::drop-down { border: none; width: 18px; }
        QComboBox:hover, QPushButton:hover {
            background: rgba(43,183,255,0.10);
            border-color: rgba(43,183,255,0.50);
        }
        QComboBox:focus { border-color: rgba(43,183,255,0.60); }

        /* ── Accent / primary button ─────────────────────────────────── */
        QPushButton#PrimaryBtn {
            background: rgba(43,183,255,0.12);
            border: 1px solid rgba(43,183,255,0.55);
            color: #2BB7FF;
            font-weight: 600;
        }
        QPushButton#PrimaryBtn:hover {
            background: rgba(43,183,255,0.22);
            border-color: rgba(43,183,255,0.75);
        }

        /* ── Flag buttons ────────────────────────────────────────────── */
        QPushButton#FlagBtn, QPushButton#FlagYellow,
        QPushButton#FlagGreen, QPushButton#FlagRed {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 8px;
            min-width: 58px;
            min-height: 26px;
            font-size: 11px;
            font-weight: 600;
            padding: 2px 4px;
        }
        QPushButton#FlagBtn:hover {
            background: rgba(43,183,255,0.10);
            border-color: rgba(43,183,255,0.45);
        }
        QPushButton#FlagYellow:hover  { background: rgba(255,200,0,0.10);  border-color: rgba(255,200,0,0.4); }
        QPushButton#FlagGreen:hover   { background: rgba(0,210,90,0.10);   border-color: rgba(0,210,90,0.4);  }
        QPushButton#FlagRed:hover     { background: rgba(255,55,55,0.10);  border-color: rgba(255,55,55,0.4); }

        QPushButton#FlagYellow:checked {
            background: rgba(255,200,0,0.18);
            border-color: rgba(255,200,0,0.65);
            color: #FFC800;
        }
        QPushButton#FlagGreen:checked {
            background: rgba(0,210,90,0.18);
            border-color: rgba(0,210,90,0.65);
            color: #00D25A;
        }
        QPushButton#FlagRed:checked {
            background: rgba(255,55,55,0.18);
            border-color: rgba(255,55,55,0.65);
            color: #FF3737;
        }

        /* ── Table ───────────────────────────────────────────────────── */
        QTableWidget {
            background: #070B14;
            alternate-background-color: #0D1320;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 14px;
            gridline-color: rgba(255,255,255,0.04);
            color: rgba(255,255,255,0.88);
            font-size: 12px;
            selection-background-color: rgba(43,183,255,0.18);
            selection-color: #fff;
        }
        QTableWidget::item { padding: 5px 10px; }
        QTableWidget::item:selected {
            background: rgba(43,183,255,0.18);
            color: #fff;
        }
        QHeaderView {
            background: transparent;
        }
        QHeaderView::section {
            background: #0C1220;
            border: none;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            border-right: 1px solid rgba(255,255,255,0.05);
            padding: 7px 10px;
            color: rgba(43,183,255,0.80);
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        QScrollBar:vertical {
            background: rgba(255,255,255,0.02);
            width: 6px;
            border-radius: 3px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: rgba(255,255,255,0.18);
            border-radius: 3px;
            min-height: 30px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """)

    # ── Root layout ───────────────────────────────────────────────────────────
    main = QVBoxLayout(root)
    main.setContentsMargins(10, 8, 10, 8)
    main.setSpacing(6)

    # ─────────────────────────────────────────────────────────────────────────
    # TOP CONTROL BAR — altezza fissa 185px, tabella prende il resto
    # Ordine: [Session Info] [Service] [Race Control >>>] [Flag Control]
    # ─────────────────────────────────────────────────────────────────────────
    ctrl_widget = QWidget()
    ctrl_widget.setFixedHeight(185)
    ctrl_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    topbar = QHBoxLayout(ctrl_widget)
    topbar.setContentsMargins(0, 0, 0, 0)
    topbar.setSpacing(8)

    # ── helper: glass panel con titolo ───────────────────────────────────────
    def _panel(title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("Panel")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 10)
        lay.setSpacing(6)
        lbl = QLabel(title.upper())
        lbl.setObjectName("PanelTitle")
        lay.addWidget(lbl)
        return frame, lay

    def _key(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("InfoKey")
        return lbl

    def _val(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("InfoValue")
        return lbl

    # ═════════════════════════════════════════════════════════════════════════
    # PANEL 1 — Session Info  (colonna singola: 4 righe key+val)
    # ═════════════════════════════════════════════════════════════════════════
    p_info, p_info_lay = _panel("Session Info")
    p_info.setFixedWidth(160)

    timer_val   = _val("00:00")
    sc_time_val = _val("00:00")
    session_val = _val("Practice")
    pit_val     = _val("Closed")

    info_grid = QGridLayout()
    info_grid.setHorizontalSpacing(8)
    info_grid.setVerticalSpacing(2)
    info_grid.setColumnStretch(1, 1)

    for row, (k, v) in enumerate([
        ("Tempo",    timer_val),
        ("SC",       sc_time_val),
        ("Sessione", session_val),
        ("Pit",      pit_val),
    ]):
        info_grid.addWidget(_key(k), row, 0, Qt.AlignVCenter)
        info_grid.addWidget(v,       row, 1, Qt.AlignVCenter)

    p_info_lay.addStretch(1)
    p_info_lay.addLayout(info_grid)
    p_info_lay.addStretch(1)
    topbar.addWidget(p_info)

    # ═════════════════════════════════════════════════════════════════════════
    # PANEL 2 — Service
    # Layout: IP: value | Live [badge] / Pre Race: combo btn / Debug
    # ═════════════════════════════════════════════════════════════════════════
    p_svc, p_svc_lay = _panel("Service")
    p_svc.setFixedWidth(250)

    ip_val = QLabel("NONE")
    ip_val.setObjectName("InfoValue")

    live_btn        = _btn("Live", 54)
    live_status_lbl = QLabel("OFF")
    live_status_lbl.setObjectName("LiveBadge")
    live_status_lbl.setMinimumWidth(44)
    live_status_lbl.setAlignment(Qt.AlignCenter)
    debug_btn = _btn("Debug")

    pre_minutes = QComboBox()
    pre_minutes.addItems(["1", "2", "3", "5", "10", "15"])
    pre_minutes.setFixedWidth(58)
    pre_btn = _btn("Start Pre-Gara")

    # Row 0: IP: [value]  Live [OFF]
    svc_r0 = QHBoxLayout()
    svc_r0.setSpacing(6)
    svc_r0.addWidget(_key("IP:"))
    svc_r0.addWidget(ip_val, 1)
    svc_r0.addWidget(live_btn)
    svc_r0.addWidget(live_status_lbl)

    # Row 1: Pre Race: [combo] [Start Pre-Gara]
    svc_r1 = QHBoxLayout()
    svc_r1.setSpacing(6)
    svc_r1.addWidget(_key("Pre Race:"))
    svc_r1.addWidget(pre_minutes)
    svc_r1.addWidget(pre_btn, 1)

    # Row 2: Debug (full-width)
    svc_r2 = QHBoxLayout()
    svc_r2.addWidget(debug_btn, 1)

    p_svc_lay.addStretch(1)
    p_svc_lay.addLayout(svc_r0)
    p_svc_lay.addLayout(svc_r1)
    p_svc_lay.addLayout(svc_r2)
    p_svc_lay.addStretch(1)
    topbar.addWidget(p_svc)

    # ═════════════════════════════════════════════════════════════════════════
    # PANEL 3 — Race Control
    # Griglia 3 righe × 2 colonne (sinistra: label+combo | destra: btn azione)
    #
    #  [Sess:]  [─── session_combo ───]  │  [Carica]
    #  [Lista:] [─── racelist_combo ──]  │  [▶ Start]  [↺ Reset]
    #  [Stato:] [status_combo][Set]      │  [Generate Result]  [Analytics]
    # ═════════════════════════════════════════════════════════════════════════
    p_race, p_race_lay = _panel("Race Control")
    p_race.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    session_box = QComboBox()
    session_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    racelist_box = QComboBox()
    racelist_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    status_box = QComboBox()
    status_box.addItems(["DNF", "DSQ", "DNS"])
    status_box.setMinimumWidth(88)

    device_btn = QToolButton()
    device_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    device_btn.setFixedWidth(92)
    device_btn.setFixedHeight(28)
    device_btn.setText("Dispositivi ▸")
    device_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    device_btn.setToolTip("Clicca per aprire la finestra dispositivi (non bloccante)")

    recovery_btn = _btn("↻  Ripristina", 100)
    recovery_btn.setToolTip("Ripristina la sessione dall'ultimo checkpoint")
    recovery_btn.setEnabled(False)

    load_btn         = _btn("Carica", 76)
    start_btn = _StartButton()
    start_btn.setCursor(Qt.PointingHandCursor)
    start_btn.setObjectName("PrimaryBtn")
    start_btn.setText("Start")   # → "▶  Start" via _StartButton.setText
    reset_btn        = _btn("↺  Reset")
    save_btn         = _btn("Generate Result")
    analytics_btn    = _btn("Analytics")
    apply_status_btn = _btn("Set", 52)

    # QGridLayout con separatore verticale tra le due metà
    rc_grid = QGridLayout()
    rc_grid.setHorizontalSpacing(6)
    rc_grid.setVerticalSpacing(7)
    # col 0: label  col 1: combo (stretch)  col 2: piccolo btn su combo
    # col 3: sep    col 4,5: btn azione (stretch uguale)
    rc_grid.setColumnStretch(1, 2)   # combo si espande
    rc_grid.setColumnStretch(4, 1)
    rc_grid.setColumnStretch(5, 1)

    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setFixedWidth(1)
    sep.setStyleSheet("background: rgba(255,255,255,0.08); border:none;")

    # Riga 0: Sessione | Carica
    rc_grid.addWidget(_key("Sess:"),     0, 0, Qt.AlignVCenter | Qt.AlignRight)
    rc_grid.addWidget(session_box,       0, 1, 1, 2, Qt.AlignVCenter)
    rc_grid.addWidget(sep,               0, 3, 3, 1)
    rc_grid.addWidget(load_btn,          0, 4, 1, 2, Qt.AlignVCenter)

    # Riga 1: Lista | Start  Reset
    rc_grid.addWidget(_key("Lista:"),    1, 0, Qt.AlignVCenter | Qt.AlignRight)
    rc_grid.addWidget(racelist_box,      1, 1, 1, 2, Qt.AlignVCenter)
    rc_grid.addWidget(start_btn,         1, 4, Qt.AlignVCenter)
    rc_grid.addWidget(reset_btn,         1, 5, Qt.AlignVCenter)

    # Riga 2: Stato combo Set | GenResult  Analytics
    rc_grid.addWidget(_key("Stato:"),    2, 0, Qt.AlignVCenter | Qt.AlignRight)
    rc_grid.addWidget(status_box,        2, 1, Qt.AlignVCenter)
    rc_grid.addWidget(apply_status_btn,  2, 2, Qt.AlignVCenter)
    rc_grid.addWidget(save_btn,          2, 4, Qt.AlignVCenter)
    rc_grid.addWidget(analytics_btn,     2, 5, Qt.AlignVCenter)

    # Riga 3: dispositivi connessi / non connessi + recovery
    rc_grid.addWidget(_key("Disp:"),    3, 0, Qt.AlignVCenter | Qt.AlignRight)
    rc_grid.addWidget(device_btn,        3, 1, Qt.AlignVCenter)
    rc_grid.addWidget(recovery_btn,      3, 2, Qt.AlignVCenter)

    p_race_lay.setSpacing(0)
    p_race_lay.addStretch(1)
    p_race_lay.addLayout(rc_grid)
    p_race_lay.addStretch(1)
    topbar.addWidget(p_race, 1)

    # ═════════════════════════════════════════════════════════════════════════
    # PANEL 4 — Flag Control  (QGroupBox → backend chiama .setTitle())
    # ═════════════════════════════════════════════════════════════════════════
    gb_flag = QGroupBox("FLAG CONTROL")
    gb_flag.setObjectName("FlagGroup")
    gb_flag.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

    flag_grid = QGridLayout(gb_flag)
    flag_grid.setSpacing(6)
    flag_grid.setContentsMargins(8, 4, 8, 8)

    flag_defs = [
        ("YS1",   0, 0, "FlagYellow", True),
        ("YS2",   0, 1, "FlagYellow", True),
        ("YS3",   0, 2, "FlagYellow", True),
        ("SC",    0, 3, "FlagBtn",    False),
        ("VSC",   0, 4, "FlagBtn",    False),
        ("F.Lap", 0, 5, "FlagBtn",    False),
        ("Green", 1, 0, "FlagGreen",  True),
        ("Red",   1, 1, "FlagRed",    True),
        ("Clear", 1, 2, "FlagBtn",    False),
        ("Wet R", 1, 3, "FlagBtn",    False),
        ("OP Pit",1, 4, "FlagBtn",    False),
        ("CL Pit",1, 5, "FlagBtn",    False),
    ]
    _flag_key = {
        "YS1": "YS1", "YS2": "YS2", "YS3": "YS3",
        "SC": "SC", "VSC": "VSC", "F.Lap": "F Lap",
        "Green": "Green", "Red": "Red", "Clear": "Clear",
        "Wet R": "Wet R", "OP Pit": "OP Pit", "CL Pit": "CL Pit",
    }

    btns: dict[str, QPushButton] = {}
    for label, row, col, obj_name, checkable in flag_defs:
        b = _checkable_btn(label) if checkable else _btn(label)
        b.setObjectName(obj_name)
        b.setMinimumWidth(58)
        b.setMinimumHeight(28)
        flag_grid.addWidget(b, row, col)
        btns[_flag_key[label]] = b

    topbar.addWidget(gb_flag)
    main.addWidget(ctrl_widget)

    # ─────────────────────────────────────────────────────────────────────────
    # TABLE — si espande per occupare tutto lo spazio rimanente
    # ─────────────────────────────────────────────────────────────────────────
    table = QTableWidget(0, 13)
    table.setHorizontalHeaderLabels([
        "Pos", "Pilota", "Team",
        "S1", "S2", "S3",
        "Last", "Giri", "Stato",
        "Gap", "Int", "Best", "Tempo",
    ])
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setShowGrid(True)

    hdr = table.horizontalHeader()
    hdr.setStretchLastSection(False)
    # Pos
    hdr.setSectionResizeMode(0,  QHeaderView.ResizeToContents)
    # Pilota, Team — stretch per usare lo spazio disponibile
    hdr.setSectionResizeMode(1,  QHeaderView.Stretch)
    hdr.setSectionResizeMode(2,  QHeaderView.Stretch)
    # Settori e tempi
    hdr.setSectionResizeMode(3,  QHeaderView.ResizeToContents)
    hdr.setSectionResizeMode(4,  QHeaderView.ResizeToContents)
    hdr.setSectionResizeMode(5,  QHeaderView.ResizeToContents)
    hdr.setSectionResizeMode(6,  QHeaderView.ResizeToContents)
    hdr.setSectionResizeMode(7,  QHeaderView.ResizeToContents)
    hdr.setSectionResizeMode(8,  QHeaderView.ResizeToContents)
    hdr.setSectionResizeMode(9,  QHeaderView.ResizeToContents)
    hdr.setSectionResizeMode(10, QHeaderView.ResizeToContents)
    hdr.setSectionResizeMode(11, QHeaderView.ResizeToContents)
    hdr.setSectionResizeMode(12, QHeaderView.ResizeToContents)

    main.addWidget(table, 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Refs
    # ─────────────────────────────────────────────────────────────────────────
    refs = RaceManagerWindowRefs(
        timer_value           = timer_val,
        sc_time_value         = sc_time_val,
        session_value         = session_val,
        pit_label             = pit_val,
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
        device_btn            = device_btn,
        recovery_btn          = recovery_btn,
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
