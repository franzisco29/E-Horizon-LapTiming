# UI/SettingsWindow/settings_window_ui.py
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QComboBox,
    QFrame, QScrollArea, QStackedWidget,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _divider() -> QFrame:
    d = QFrame()
    d.setObjectName("SectionDivider")
    return d


def _field_label(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("FieldLabel")
    return lb


def _hint_label(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("HintLabel")
    lb.setWordWrap(True)
    return lb


def _group_title(icon: str, text: str) -> QLabel:
    lb = QLabel(f"{icon}  {text}")
    lb.setObjectName("GroupTitle")
    return lb


def _nav_btn(icon: str, text: str) -> QPushButton:
    btn = QPushButton(f"  {icon}  {text}")
    btn.setObjectName("NavBtn")
    btn.setCheckable(True)
    btn.setFixedHeight(44)
    return btn


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

    _STYLE = """
        /* ====== Root ====== */
        QWidget#SettingsWindowUI {
            background: #060A10;
            color: #EAF2FF;
            font-family: "Google Sans";
            font-size: 10pt;
        }

        /* ====== Sidebar ====== */
        QWidget#Sidebar {
            background: #0A0F1A;
            border-right: 1px solid #131D2B;
        }
        QLabel#AppTitle {
            font-family: "Audiowide";
            font-size: 14pt;
            letter-spacing: 1px;
            color: #EAF2FF;
        }
        QLabel#AppSubtitle {
            font-size: 7.5pt;
            color: #4A6880;
            letter-spacing: 0.8px;
        }
        QLabel#ProfileBadge {
            font-size: 8pt;
            font-weight: 700;
            color: #00A6FF;
            background: rgba(0,166,255,0.10);
            border: 1px solid rgba(0,166,255,0.32);
            border-radius: 8px;
            padding: 2px 10px;
        }
        QLabel#NavSection {
            font-size: 7pt;
            font-weight: 700;
            color: #3D607E;
            letter-spacing: 1.5px;
            padding: 0 0 0 14px;
        }
        QPushButton#NavBtn {
            background: transparent;
            border: none;
            border-radius: 10px;
            color: #5A7A9A;
            font-size: 10pt;
            font-weight: 500;
            text-align: left;
            padding-left: 14px;
        }
        QPushButton#NavBtn:hover {
            background: rgba(255,255,255,0.028);
            color: #8AAAC8;
        }
        QPushButton#NavBtn:checked {
            background: rgba(0,166,255,0.11);
            color: #D8EEFF;
            font-weight: 700;
            border-left: 3px solid #00A6FF;
        }

        /* ====== Content area ====== */
        QWidget#ContentArea { background: #060A10; }
        QScrollArea {
            border: none;
            background: transparent;
        }
        QScrollArea > QWidget > QWidget { background: transparent; }

        /* ====== Cards ====== */
        QFrame#Card {
            background: #0B1120;
            border: 1px solid #131F32;
            border-radius: 18px;
        }
        QFrame#Card:disabled {
            background: #080D18;
            border: 1px solid #0E1820;
        }
        QFrame#InnerCard {
            background: #08111E;
            border: 1px solid #10192A;
            border-radius: 12px;
        }
        QFrame#SectionDivider {
            background: #10192A;
            min-height: 1px;
            max-height: 1px;
            border: none;
        }

        /* ====== Typography ====== */
        QLabel { background: transparent; }
        QLabel#PageTitle {
            font-size: 17pt;
            font-weight: 700;
            color: #D0E8FF;
            letter-spacing: 0.3px;
        }
        QLabel#PageSubtitle {
            font-size: 9pt;
            color: #4A6880;
        }
        QLabel#GroupTitle {
            font-size: 11pt;
            font-weight: 700;
            color: #A8C8E8;
        }
        QLabel#FieldLabel {
            color: #5A8AAB;
            font-size: 9.5pt;
        }
        QLabel#FieldValue {
            color: #C0D8F4;
            font-size: 10pt;
            font-weight: 600;
        }
        QLabel#HintLabel {
            color: #4A6878;
            font-size: 8.5pt;
        }
        QLabel#SummarySection {
            font-size: 7pt;
            font-weight: 700;
            color: #3D607E;
            letter-spacing: 1.2px;
        }

        /* ====== Inputs ====== */
        QLineEdit {
            height: 40px;
            border-radius: 12px;
            padding: 0 14px;
            background: #070E1A;
            border: 1px solid #131F32;
            color: #C8E0F8;
            font-size: 10pt;
        }
        QLineEdit:focus {
            border: 1px solid #00A6FF;
            background: #080F1C;
        }
        QLineEdit:disabled {
            background: #060B14;
            border: 1px solid #0C1520;
            color: rgba(200,224,248,0.22);
        }
        QComboBox {
            height: 40px;
            border-radius: 12px;
            padding: 0 12px;
            background: #070E1A;
            border: 1px solid #131F32;
            color: #C8E0F8;
            font-size: 10pt;
        }
        QComboBox:focus { border: 1px solid #00A6FF; }
        QComboBox::drop-down { border: none; width: 28px; }
        QComboBox QAbstractItemView {
            background: #070E1A;
            border: 1px solid #131F32;
            selection-background-color: #0D1C30;
            color: #C8E0F8;
            outline: none;
        }
        QComboBox:disabled {
            background: #060B14;
            border: 1px solid #0C1520;
            color: rgba(200,224,248,0.22);
        }
        QCheckBox {
            spacing: 10px;
            color: #A8C8E8;
            font-size: 10pt;
            font-weight: 500;
            padding: 7px 10px;
            border-radius: 10px;
            min-height: 32px;
            background: transparent;
        }
        QCheckBox:hover { background: rgba(255,255,255,0.024); }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border-radius: 7px;
            border: 1px solid #192C42;
            background: #070E1A;
        }
        QCheckBox::indicator:checked {
            background: #00A6FF;
            border: 1px solid #00A6FF;
        }
        QCheckBox:disabled { color: rgba(168,200,232,0.22); }
        QCheckBox::indicator:disabled {
            background: #060B14;
            border: 1px solid #0C1520;
        }

        /* ====== Buttons ====== */
        QPushButton {
            border-radius: 12px;
            padding: 10px 18px;
            background: #0C1828;
            border: 1px solid #131F32;
            color: #7090B0;
            font-size: 10pt;
        }
        QPushButton:hover {
            background: #0F1E30;
            border: 1px solid rgba(0,166,255,0.38);
            color: #C0D8F4;
        }
        QPushButton#Primary {
            background: rgba(0,166,255,0.12);
            border: 1px solid rgba(0,166,255,0.60);
            color: #D8F0FF;
            font-weight: 700;
        }
        QPushButton#Primary:hover { background: rgba(0,166,255,0.20); }
        QPushButton:disabled {
            background: #07101A;
            border: 1px solid #0E1820;
            color: rgba(112,144,176,0.22);
        }

        /* ====== Bottom bar ====== */
        QWidget#BottomBar {
            background: #07101A;
            border-top: 1px solid #101E30;
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsWindowUI")
        self.setWindowTitle("E-Horizon \u2022 Impostazioni")
        self.setMinimumSize(980, 640)
        self.setStyleSheet(self._STYLE)

        # ===== Root layout: sidebar | content =====
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar = QWidget(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(224)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(14, 26, 14, 20)
        sb.setSpacing(0)

        app_title = QLabel("E-HORIZON")
        app_title.setObjectName("AppTitle")
        app_subtitle = QLabel("LAP TIMING SYSTEM")
        app_subtitle.setObjectName("AppSubtitle")
        sb.addWidget(app_title)
        sb.addWidget(app_subtitle)
        sb.addSpacing(20)

        title_label = QLabel("ADMIN")
        title_label.setObjectName("ProfileBadge")
        title_label.setFixedHeight(24)
        sb.addWidget(title_label, alignment=Qt.AlignLeft)
        sb.addSpacing(28)

        nav_lbl = QLabel("SEZIONI")
        nav_lbl.setObjectName("NavSection")
        sb.addWidget(nav_lbl)
        sb.addSpacing(8)

        self._nav_btns: list[QPushButton] = []
        _nav_items = [
            ("\u2699",   "Generale"),
            ("\U0001f4e1", "Comunicazione"),
            ("\U0001f50c", "Dispositivi"),
            ("\U0001f4fa", "Live Timing"),
            ("\U0001f4c1", "Cartelle"),
        ]
        for icon, label in _nav_items:
            btn = _nav_btn(icon, label)
            self._nav_btns.append(btn)
            sb.addWidget(btn)
            sb.addSpacing(3)

        sb.addStretch(1)

        # Summary mini-card at the bottom of the sidebar
        sum_frame = QFrame()
        sum_frame.setObjectName("InnerCard")
        sf = QGridLayout(sum_frame)
        sf.setContentsMargins(12, 12, 12, 12)
        sf.setHorizontalSpacing(8)
        sf.setVerticalSpacing(8)
        sf.setColumnStretch(1, 1)
        sf.setColumnMinimumWidth(0, 70)

        sf_title = QLabel("STATO RAPIDO")
        sf_title.setObjectName("SummarySection")
        sf.addWidget(sf_title, 0, 0, 1, 2)

        summary_conn_value    = QLabel("-")
        summary_start_value   = QLabel("-")
        summary_live_value    = QLabel("-")
        summary_profile_value = QLabel("-")

        for idx, (txt, val) in enumerate([
            ("Connessione", summary_conn_value),
            ("Start",       summary_start_value),
            ("Live",        summary_live_value),
            ("Profilo",     summary_profile_value),
        ], start=1):
            fl = _field_label(txt)
            fl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            val.setObjectName("FieldValue")
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            sf.addWidget(fl,  idx, 0)
            sf.addWidget(val, idx, 1)

        sb.addWidget(sum_frame)
        root.addWidget(sidebar)

        # ── Right side: scrollable pages + bottom bar ─────────────────────────
        right_vbox = QVBoxLayout()
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)

        content_host = QWidget(self)
        content_host.setObjectName("ContentArea")
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content_host)

        ch_vbox = QVBoxLayout(content_host)
        ch_vbox.setContentsMargins(0, 0, 0, 0)
        ch_vbox.setSpacing(0)

        self._stack = QStackedWidget(content_host)
        ch_vbox.addWidget(self._stack)
        right_vbox.addWidget(scroll, 1)

        # Bottom bar
        bottom_bar = QWidget(self)
        bottom_bar.setObjectName("BottomBar")
        bottom_bar.setFixedHeight(62)
        bb = QHBoxLayout(bottom_bar)
        bb.setContentsMargins(28, 0, 28, 0)
        bb.setSpacing(12)
        bb.addStretch(1)

        cancel_btn = QPushButton("Annulla")
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setFixedHeight(40)

        save_btn = QPushButton("  Salva impostazioni  ")
        save_btn.setObjectName("Primary")
        save_btn.setFixedHeight(40)
        save_btn.setMinimumWidth(190)

        bb.addWidget(cancel_btn)
        bb.addWidget(save_btn)
        right_vbox.addWidget(bottom_bar)

        right_widget = QWidget(self)
        right_widget.setLayout(right_vbox)
        root.addWidget(right_widget, 1)

        # ── Build pages ───────────────────────────────────────────────────────
        (
            monitor_combo, debug_check, live_check, tv_check,
            manual_start_check,
            conn_type_combo, debounce_edit,
            tcp_ip_value_label, tcp_port_edit, tcp_card,
            dev_checks,
            live_ip_edit, live_port_edit, live_public_check, live_box,
            root_path_edit, browse_btn,
            starting_box,
        ) = self._build_pages()

        for i, btn in enumerate(self._nav_btns):
            btn.clicked.connect(lambda _chk, idx=i: self._go_to_page(idx))
        self._nav_btns[0].setChecked(True)

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
            title_label=title_label,
        )

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def _go_to_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == index)

    # -------------------------------------------------------------------------
    # Page factory helpers
    # -------------------------------------------------------------------------

    def _make_page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("ContentArea")
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(32, 28, 32, 32)
        vbox.setSpacing(18)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("PageTitle")
        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("PageSubtitle")
        vbox.addWidget(title_lbl)
        vbox.addWidget(sub_lbl)
        vbox.addWidget(_divider())
        return page, vbox

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("Card")
        inner = QVBoxLayout(card)
        inner.setContentsMargins(22, 18, 22, 20)
        inner.setSpacing(14)
        return card, inner

    def _field_row(self, layout: QGridLayout, row: int,
                   label: str, widget: QWidget, hint: str = "") -> None:
        lbl = _field_label(label)
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(lbl, row, 0)
        layout.addWidget(widget, row, 1)
        if hint:
            layout.addWidget(_hint_label(hint), row + 1, 0, 1, 2)

    # -------------------------------------------------------------------------
    # Page 0 — Generale
    # -------------------------------------------------------------------------

    def _build_page_generale(self):
        page, vbox = self._make_page(
            "Generale",
            "Monitor di output, modalit\u00e0 debug e comportamento della gara"
        )

        card_disp, inner_disp = self._card()
        inner_disp.addWidget(_group_title("\U0001f5a5", "Display"))
        inner_disp.addWidget(_divider())
        g = QGridLayout()
        g.setHorizontalSpacing(20)
        g.setVerticalSpacing(14)
        g.setColumnMinimumWidth(0, 190)
        g.setColumnStretch(1, 1)
        monitor_combo = QComboBox()
        self._field_row(g, 0, "Monitor di output", monitor_combo,
                        "Seleziona lo schermo su cui mostrare la finestra di gara.")
        inner_disp.addLayout(g)
        vbox.addWidget(card_disp)

        card_mode, inner_mode = self._card()
        inner_mode.addWidget(_group_title("\U0001f527", "Modalit\u00e0 operative"))
        inner_mode.addWidget(_divider())
        debug_check = QCheckBox("Abilita modalit\u00e0 Debug")
        debug_check.setToolTip("Mostra informazioni aggiuntive nei log e nella UI.")
        inner_mode.addWidget(debug_check)
        manual_start_check = QCheckBox("Start manuale gara")
        manual_start_check.setToolTip("Abilita la sequenza manuale di start (START_PROC).")
        inner_mode.addWidget(manual_start_check)
        inner_mode.addWidget(_hint_label(
            "Se disabilitato, lo start avviene automaticamente senza "
            "intervento dell\u2019operatore."
        ))
        vbox.addWidget(card_mode)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return monitor_combo, debug_check, manual_start_check

    # -------------------------------------------------------------------------
    # Page 1 — Comunicazione
    # -------------------------------------------------------------------------

    def _build_page_comunicazione(self):
        page, vbox = self._make_page(
            "Comunicazione",
            "Protocollo di rete e parametri della connessione TCP"
        )

        card_prot, inner_prot = self._card()
        inner_prot.addWidget(_group_title("\U0001f4e1", "Protocollo"))
        inner_prot.addWidget(_divider())
        g = QGridLayout()
        g.setHorizontalSpacing(20)
        g.setVerticalSpacing(14)
        g.setColumnMinimumWidth(0, 190)
        g.setColumnStretch(1, 1)
        conn_type_combo = QComboBox()
        conn_type_combo.addItems(["NONE \u2013 Nessuna connessione", "TCP", "SERIAL", "WiFi UDP"])
        self._field_row(g, 0, "Tipo di comunicazione", conn_type_combo)
        debounce_edit = QLineEdit()
        debounce_edit.setPlaceholderText("es. 3000")
        self._field_row(g, 1, "DeBounce Time (ms)", debounce_edit,
                        "Tempo minimo tra due passaggi sullo stesso rilevatore.")
        inner_prot.addLayout(g)
        vbox.addWidget(card_prot)

        tcp_card = QFrame()
        tcp_card.setObjectName("Card")
        tc = QVBoxLayout(tcp_card)
        tc.setContentsMargins(22, 18, 22, 20)
        tc.setSpacing(14)
        tc.addWidget(_group_title("\U0001f517", "TCP Connection"))
        tc.addWidget(_divider())
        tg = QGridLayout()
        tg.setHorizontalSpacing(20)
        tg.setVerticalSpacing(14)
        tg.setColumnMinimumWidth(0, 190)
        tg.setColumnStretch(1, 1)
        tcp_ip_value_label = QLabel("-")
        tcp_ip_value_label.setObjectName("FieldValue")
        self._field_row(tg, 0, "IP locale applicazione", tcp_ip_value_label)
        tcp_port_edit = QLineEdit()
        tcp_port_edit.setPlaceholderText("es. 20777")
        self._field_row(tg, 1, "Porta TCP", tcp_port_edit)
        tc.addLayout(tg)
        vbox.addWidget(tcp_card)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return conn_type_combo, debounce_edit, tcp_ip_value_label, tcp_port_edit, tcp_card

    # -------------------------------------------------------------------------
    # Page 2 — Dispositivi
    # -------------------------------------------------------------------------

    def _build_page_dispositivi(self):
        page, vbox = self._make_page(
            "Dispositivi",
            "Abilita i rilevatori fisicamente presenti nel circuito"
        )

        card, inner = self._card()
        inner.addWidget(_group_title("\U0001f50c", "Rilevatori attivi"))
        inner.addWidget(_divider())
        inner.addWidget(_hint_label(
            "Seleziona i dispositivi fisicamente collegati. "
            "La Centrale \u00e8 sempre necessaria per l\u2019avvio della sessione."
        ))

        names_desc = [
            ("Centrale",  "Dispositivo master \u2013 obbligatorio"),
            ("Settore 1", "Rilevatore intermedio settore 1"),
            ("Settore 2", "Rilevatore intermedio settore 2"),
            ("Pit In",    "Ingresso corsia box"),
            ("Pit Out",   "Uscita corsia box"),
            ("Semaforo",  "Pannello semaforico di partenza"),
        ]
        dev_checks: list[QCheckBox] = []
        dg = QGridLayout()
        dg.setHorizontalSpacing(24)
        dg.setVerticalSpacing(4)

        for i, (name, desc) in enumerate(names_desc):
            cb = QCheckBox(name)
            cb.setToolTip(desc)
            dev_checks.append(cb)
            row, col = divmod(i, 2)
            cell = QVBoxLayout()
            cell.setSpacing(0)
            cell.addWidget(cb)
            cell.addWidget(_hint_label(desc))
            dg.addLayout(cell, row, col)

        inner.addLayout(dg)
        vbox.addWidget(card)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return dev_checks

    # -------------------------------------------------------------------------
    # Page 3 — Live Timing
    # -------------------------------------------------------------------------

    def _build_page_live(self):
        page, vbox = self._make_page(
            "Live Timing",
            "Configurazione del server live e trasmissione dati in tempo reale"
        )

        card_en, inner_en = self._card()
        inner_en.addWidget(_group_title("\U0001f4fa", "Attivazione"))
        inner_en.addWidget(_divider())
        live_check = QCheckBox("Attiva Live Timing")
        live_check.setToolTip("Abilita la trasmissione dati live verso i client browser.")
        inner_en.addWidget(live_check)
        tv_check = QCheckBox("Attiva Tv Tower (non disponibile)")
        tv_check.setToolTip("Opzione non disponibile in questa versione.")
        inner_en.addWidget(tv_check)
        vbox.addWidget(card_en)

        live_box = QFrame()
        live_box.setObjectName("Card")
        lb = QVBoxLayout(live_box)
        lb.setContentsMargins(22, 18, 22, 20)
        lb.setSpacing(14)
        lb.addWidget(_group_title("\U0001f310", "Server Live"))
        lb.addWidget(_divider())
        lg = QGridLayout()
        lg.setHorizontalSpacing(20)
        lg.setVerticalSpacing(14)
        lg.setColumnMinimumWidth(0, 190)
        lg.setColumnStretch(1, 1)
        live_ip_edit = QLineEdit()
        live_ip_edit.setPlaceholderText("es. 127.0.0.1")
        self._field_row(lg, 0, "IP server live", live_ip_edit)
        live_port_edit = QLineEdit()
        live_port_edit.setPlaceholderText("es. 8080")
        self._field_row(lg, 1, "Porta server live", live_port_edit)
        lb.addLayout(lg)
        lb.addWidget(_divider())
        live_public_check = QCheckBox("Tunnel pubblico via ngrok")
        live_public_check.setToolTip("Espone il server live su URL pubblico tramite ngrok.")
        lb.addWidget(live_public_check)
        lb.addWidget(_hint_label(
            "Richiede ngrok configurato e autenticato. "
            "Consente l\u2019accesso esterno alla pagina live dal browser."
        ))
        vbox.addWidget(live_box)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return live_check, tv_check, live_ip_edit, live_port_edit, live_public_check, live_box

    # -------------------------------------------------------------------------
    # Page 4 — Cartelle
    # -------------------------------------------------------------------------

    def _build_page_cartelle(self):
        page, vbox = self._make_page(
            "Cartelle",
            "Percorso radice per sessioni, classifiche e database"
        )

        starting_box = QFrame()  # kept for SettingsWindowUIRefs compatibility

        card, inner = self._card()
        inner.addWidget(_group_title("\U0001f4c1", "Cartella dati"))
        inner.addWidget(_divider())
        inner.addWidget(_hint_label(
            "Tutte le sessioni, classifiche e database vengono salvati in questa cartella. "
            "Modificare solo se necessario e riavviare l\u2019applicazione."
        ))

        root_path_edit = QLineEdit()
        root_path_edit.setPlaceholderText("C:\\Users\\...\\data")
        browse_btn = QPushButton("  Sfoglia\u2026")
        browse_btn.setFixedHeight(40)
        browse_btn.setMinimumWidth(110)
        browse_btn.setToolTip("Seleziona una cartella diversa")

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.addWidget(root_path_edit, 1)
        path_row.addWidget(browse_btn, 0)

        fg = QGridLayout()
        fg.setHorizontalSpacing(12)
        fg.setVerticalSpacing(14)
        fg.setColumnMinimumWidth(0, 190)
        fg.setColumnStretch(1, 1)
        fg.addWidget(_field_label("Percorso cartella dati"), 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        fg.addLayout(path_row, 0, 1)

        inner.addLayout(fg)
        vbox.addWidget(card)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return root_path_edit, browse_btn, starting_box

    # -------------------------------------------------------------------------
    # Orchestrate
    # -------------------------------------------------------------------------

    def _build_pages(self):
        monitor_combo, debug_check, manual_start_check = self._build_page_generale()
        (conn_type_combo, debounce_edit,
         tcp_ip_value_label, tcp_port_edit, tcp_card) = self._build_page_comunicazione()
        dev_checks = self._build_page_dispositivi()
        (live_check, tv_check, live_ip_edit,
         live_port_edit, live_public_check, live_box) = self._build_page_live()
        root_path_edit, browse_btn, starting_box = self._build_page_cartelle()

        return (
            monitor_combo, debug_check, live_check, tv_check,
            manual_start_check,
            conn_type_combo, debounce_edit,
            tcp_ip_value_label, tcp_port_edit, tcp_card,
            dev_checks,
            live_ip_edit, live_port_edit, live_public_check, live_box,
            root_path_edit, browse_btn,
            starting_box,
        )
