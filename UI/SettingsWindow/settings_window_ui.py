from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


def _divider() -> QFrame:
    frame = QFrame()
    frame.setObjectName("SectionDivider")
    return frame


def _field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    return label


def _hint_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("HintLabel")
    label.setWordWrap(True)
    return label


def _group_title(icon: str, text: str) -> QLabel:
    label = QLabel(f"{icon}  {text}")
    label.setObjectName("GroupTitle")
    return label


def _nav_btn(icon: str, text: str) -> QPushButton:
    button = QPushButton(f"  {icon}  {text}")
    button.setObjectName("NavBtn")
    button.setCheckable(True)
    button.setFixedHeight(44)
    return button


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
    heartbeat_interval_edit: QLineEdit
    heartbeat_max_missed_edit: QLineEdit
    live_ip_edit: QLineEdit
    live_port_edit: QLineEdit
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
        QWidget#SettingsWindowUI {
            background: #060A10;
            color: #EAF2FF;
            font-family: "Google Sans";
            font-size: 10pt;
        }
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
        QWidget#ContentArea { background: #060A10; }
        QScrollArea { border: none; background: transparent; }
        QScrollArea > QWidget > QWidget { background: transparent; }
        QFrame#Card {
            background: #0B1120;
            border: 1px solid #131F32;
            border-radius: 18px;
        }
        QFrame#SectionDivider {
            background: #10192A;
            min-height: 1px;
            max-height: 1px;
            border: none;
        }
        QLabel { background: transparent; }
        QLabel#PageTitle {
            font-size: 17pt;
            font-weight: 700;
            color: #D0E8FF;
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
        QLineEdit, QComboBox {
            height: 40px;
            border-radius: 12px;
            padding: 0 14px;
            background: #070E1A;
            border: 1px solid #131F32;
            color: #C8E0F8;
            font-size: 10pt;
        }
        QLineEdit:focus, QComboBox:focus { border: 1px solid #00A6FF; }
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
        QWidget#BottomBar {
            background: #07101A;
            border-top: 1px solid #101E30;
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsWindowUI")
        self.setWindowTitle("E-Horizon • Impostazioni")
        self.setMinimumSize(980, 640)
        self.setStyleSheet(self._STYLE)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

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
        for icon, label in [
            ("⚙", "Generale"),
            ("📡", "Comunicazione"),
            ("⏱", "Heartbeat"),
            ("🔌", "Dispositivi"),
            ("📺", "Live Timing"),
            ("📁", "Cartelle"),
        ]:
            btn = _nav_btn(icon, label)
            self._nav_btns.append(btn)
            sb.addWidget(btn)
            sb.addSpacing(3)

        sb.addStretch(1)

        summary_box = QFrame()
        summary_box.setObjectName("Card")
        summary_layout = QGridLayout(summary_box)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setHorizontalSpacing(8)
        summary_layout.setVerticalSpacing(8)
        summary_layout.setColumnStretch(1, 1)
        summary_layout.setColumnMinimumWidth(0, 70)

        summary_title = QLabel("STATO RAPIDO")
        summary_title.setObjectName("GroupTitle")
        summary_layout.addWidget(summary_title, 0, 0, 1, 2)

        summary_conn_value = QLabel("-")
        summary_start_value = QLabel("-")
        summary_live_value = QLabel("-")
        summary_profile_value = QLabel("-")

        for row, (label_text, value_widget) in enumerate(
            [
                ("Connessione", summary_conn_value),
                ("Start", summary_start_value),
                ("Live", summary_live_value),
                ("Profilo", summary_profile_value),
            ],
            start=1,
        ):
            label = _field_label(label_text)
            value_widget.setObjectName("FieldValue")
            summary_layout.addWidget(label, row, 0)
            summary_layout.addWidget(value_widget, row, 1)

        sb.addWidget(summary_box)
        root.addWidget(sidebar)

        content_host = QWidget(self)
        content_host.setObjectName("ContentArea")
        content_layout = QVBoxLayout(content_host)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content_host)

        self._stack = QStackedWidget(content_host)
        content_layout.addWidget(self._stack)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(0)
        right_column.addWidget(scroll, 1)

        bottom_bar = QWidget(self)
        bottom_bar.setObjectName("BottomBar")
        bottom_bar.setFixedHeight(62)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(28, 0, 28, 0)
        bottom_layout.setSpacing(12)
        bottom_layout.addStretch(1)

        cancel_btn = QPushButton("Annulla")
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setFixedHeight(40)

        save_btn = QPushButton("  Salva impostazioni  ")
        save_btn.setObjectName("Primary")
        save_btn.setFixedHeight(40)
        save_btn.setMinimumWidth(190)

        bottom_layout.addWidget(cancel_btn)
        bottom_layout.addWidget(save_btn)
        right_column.addWidget(bottom_bar)

        right_widget = QWidget(self)
        right_widget.setLayout(right_column)
        root.addWidget(right_widget, 1)

        (
            monitor_combo,
            debug_check,
            live_check,
            tv_check,
            manual_start_check,
            conn_type_combo,
            debounce_edit,
            heartbeat_interval_edit,
            heartbeat_max_missed_edit,
            tcp_ip_value_label,
            tcp_port_edit,
            tcp_card,
            dev_checks,
            live_ip_edit,
            live_port_edit,
            live_box,
            root_path_edit,
            browse_btn,
            starting_box,
        ) = self._build_pages()

        for index, button in enumerate(self._nav_btns):
            button.clicked.connect(lambda checked=False, idx=index: self._go_to_page(idx))
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
            heartbeat_interval_edit=heartbeat_interval_edit,
            heartbeat_max_missed_edit=heartbeat_max_missed_edit,
            live_ip_edit=live_ip_edit,
            live_port_edit=live_port_edit,
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

    def _go_to_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for btn_index, button in enumerate(self._nav_btns):
            button.setChecked(btn_index == index)

    def _make_page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("ContentArea")
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(32, 28, 32, 32)
        vbox.setSpacing(18)
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PageSubtitle")
        vbox.addWidget(title_label)
        vbox.addWidget(subtitle_label)
        vbox.addWidget(_divider())
        return page, vbox

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(14)
        return card, layout

    def _field_row(self, layout: QGridLayout, row: int, label_text: str, widget: QWidget, hint: str = "") -> None:
        label = _field_label(label_text)
        layout.addWidget(label, row, 0)
        layout.addWidget(widget, row, 1)
        if hint:
            layout.addWidget(_hint_label(hint), row + 1, 0, 1, 2)

    def _build_page_generale(self):
        page, vbox = self._make_page("Generale", "Monitor di output, modalità debug e comportamento della gara")

        display_card, display_layout = self._card()
        display_layout.addWidget(_group_title("🖥", "Display"))
        display_layout.addWidget(_divider())
        display_grid = QGridLayout()
        display_grid.setHorizontalSpacing(20)
        display_grid.setVerticalSpacing(14)
        display_grid.setColumnMinimumWidth(0, 190)
        display_grid.setColumnStretch(1, 1)
        monitor_combo = QComboBox()
        self._field_row(display_grid, 0, "Monitor di output", monitor_combo, "Seleziona lo schermo su cui mostrare la finestra di gara.")
        display_layout.addLayout(display_grid)
        vbox.addWidget(display_card)

        mode_card, mode_layout = self._card()
        mode_layout.addWidget(_group_title("🔧", "Modalità operative"))
        mode_layout.addWidget(_divider())
        debug_check = QCheckBox("Abilita modalità Debug")
        mode_layout.addWidget(debug_check)
        manual_start_check = QCheckBox("Start manuale gara")
        mode_layout.addWidget(manual_start_check)
        mode_layout.addWidget(_hint_label("Se disabilitato, lo start avviene automaticamente senza intervento dell’operatore."))
        vbox.addWidget(mode_card)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return monitor_combo, debug_check, manual_start_check

    def _build_page_comunicazione(self):
        page, vbox = self._make_page("Comunicazione", "Protocollo di rete e parametri della connessione TCP")

        protocol_card, protocol_layout = self._card()
        protocol_layout.addWidget(_group_title("📡", "Protocollo"))
        protocol_layout.addWidget(_divider())
        protocol_grid = QGridLayout()
        protocol_grid.setHorizontalSpacing(20)
        protocol_grid.setVerticalSpacing(14)
        protocol_grid.setColumnMinimumWidth(0, 190)
        protocol_grid.setColumnStretch(1, 1)
        conn_type_combo = QComboBox()
        conn_type_combo.addItems(["NONE – Nessuna connessione", "TCP", "LAPMONITOR", "SERIAL"])
        self._field_row(protocol_grid, 0, "Tipo di comunicazione", conn_type_combo)
        debounce_edit = QLineEdit()
        debounce_edit.setPlaceholderText("es. 3000")
        self._field_row(protocol_grid, 1, "DeBounce Time (ms)", debounce_edit, "Tempo minimo tra due passaggi sullo stesso rilevatore.")
        protocol_layout.addLayout(protocol_grid)
        vbox.addWidget(protocol_card)

        tcp_card = QFrame()
        tcp_card.setObjectName("Card")
        tcp_layout = QVBoxLayout(tcp_card)
        tcp_layout.setContentsMargins(22, 18, 22, 20)
        tcp_layout.setSpacing(14)
        tcp_layout.addWidget(_group_title("🔗", "TCP Connection"))
        tcp_layout.addWidget(_divider())
        tcp_grid = QGridLayout()
        tcp_grid.setHorizontalSpacing(20)
        tcp_grid.setVerticalSpacing(14)
        tcp_grid.setColumnMinimumWidth(0, 190)
        tcp_grid.setColumnStretch(1, 1)
        tcp_ip_value_label = QLabel("-")
        tcp_ip_value_label.setObjectName("FieldValue")
        self._field_row(tcp_grid, 0, "IP locale applicazione", tcp_ip_value_label)
        tcp_port_edit = QLineEdit()
        tcp_port_edit.setPlaceholderText("es. 20777")
        self._field_row(tcp_grid, 1, "Porta TCP", tcp_port_edit)
        tcp_layout.addLayout(tcp_grid)
        vbox.addWidget(tcp_card)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return conn_type_combo, debounce_edit, tcp_ip_value_label, tcp_port_edit, tcp_card

    def _build_page_heartbeat(self):
        page, vbox = self._make_page("Heartbeat", "Parametri di keep-alive tra server e device TCP")

        card, layout = self._card()
        layout.addWidget(_group_title("⏱", "Controllo connessione"))
        layout.addWidget(_divider())
        layout.addWidget(_hint_label("Il server invia ST a intervalli regolari. Se un device non risponde S:OK per più cicli consecutivi, viene scollegato e lo slot viene liberato."))

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(14)
        grid.setColumnMinimumWidth(0, 190)
        grid.setColumnStretch(1, 1)

        heartbeat_interval_edit = QLineEdit()
        heartbeat_interval_edit.setPlaceholderText("es. 5")
        self._field_row(grid, 0, "Intervallo heartbeat (s)", heartbeat_interval_edit, "Ogni quanti secondi inviare ST a tutti i device connessi.")

        heartbeat_max_missed_edit = QLineEdit()
        heartbeat_max_missed_edit.setPlaceholderText("es. 3")
        self._field_row(grid, 2, "Heartbeat mancati massimi", heartbeat_max_missed_edit, "Numero massimo di heartbeat mancati prima di considerare il device disconnesso.")

        layout.addLayout(grid)
        vbox.addWidget(card)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return heartbeat_interval_edit, heartbeat_max_missed_edit

    def _build_page_dispositivi(self):
        page, vbox = self._make_page("Dispositivi", "Abilita i rilevatori fisicamente presenti nel circuito")

        card, layout = self._card()
        layout.addWidget(_group_title("🔌", "Rilevatori attivi"))
        layout.addWidget(_divider())
        layout.addWidget(_hint_label("Seleziona i dispositivi fisicamente collegati. La Centrale è sempre necessaria per l’avvio della sessione."))

        names_desc = [
            ("Centrale", "Dispositivo master – obbligatorio"),
            ("Settore 1", "Rilevatore intermedio settore 1"),
            ("Settore 2", "Rilevatore intermedio settore 2"),
            ("Pit In", "Ingresso corsia box"),
            ("Pit Out", "Uscita corsia box"),
            ("Semaforo", "Pannello semaforico di partenza"),
        ]
        dev_checks: list[QCheckBox] = []
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(10)
        for index, (name, desc) in enumerate(names_desc):
            checkbox = QCheckBox(name)
            checkbox.setToolTip(desc)
            dev_checks.append(checkbox)
            row, col = divmod(index, 2)
            cell = QVBoxLayout()
            cell.setSpacing(0)
            cell.addWidget(checkbox)
            cell.addWidget(_hint_label(desc))
            grid.addLayout(cell, row, col)

        layout.addLayout(grid)
        vbox.addWidget(card)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return dev_checks

    def _build_page_live(self):
        page, vbox = self._make_page("Live Timing", "Configurazione del server live e trasmissione dati in tempo reale")

        activation_card, activation_layout = self._card()
        activation_layout.addWidget(_group_title("📺", "Attivazione"))
        activation_layout.addWidget(_divider())
        live_check = QCheckBox("Attiva Live Timing")
        activation_layout.addWidget(live_check)
        tv_check = QCheckBox("Attiva Tv Tower (non disponibile)")
        activation_layout.addWidget(tv_check)
        vbox.addWidget(activation_card)

        live_box = QFrame()
        live_box.setObjectName("Card")
        live_layout = QVBoxLayout(live_box)
        live_layout.setContentsMargins(22, 18, 22, 20)
        live_layout.setSpacing(14)
        live_layout.addWidget(_group_title("🌐", "Server Live"))
        live_layout.addWidget(_divider())
        live_grid = QGridLayout()
        live_grid.setHorizontalSpacing(20)
        live_grid.setVerticalSpacing(14)
        live_grid.setColumnMinimumWidth(0, 190)
        live_grid.setColumnStretch(1, 1)
        live_ip_edit = QLineEdit()
        live_ip_edit.setPlaceholderText("es. 127.0.0.1")
        self._field_row(live_grid, 0, "IP server live", live_ip_edit)
        live_port_edit = QLineEdit()
        live_port_edit.setPlaceholderText("es. 8080")
        self._field_row(live_grid, 1, "Porta server live", live_port_edit)
        live_layout.addLayout(live_grid)
        vbox.addWidget(live_box)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        return live_check, tv_check, live_ip_edit, live_port_edit, live_box

    def _build_page_cartelle(self):
        page, vbox = self._make_page("Cartelle", "Percorso radice per sessioni, classifiche e database")

        card, layout = self._card()
        layout.addWidget(_group_title("📁", "Cartella dati"))
        layout.addWidget(_divider())
        layout.addWidget(_hint_label("Tutte le sessioni, classifiche e database vengono salvati in questa cartella. Modificare solo se necessario e riavviare l’applicazione."))

        root_path_edit = QLineEdit()
        root_path_edit.setPlaceholderText("C:\\Users\\...\\data")
        browse_btn = QPushButton("  Sfoglia…")
        browse_btn.setFixedHeight(40)
        browse_btn.setMinimumWidth(110)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.addWidget(root_path_edit, 1)
        path_row.addWidget(browse_btn, 0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(14)
        grid.setColumnMinimumWidth(0, 190)
        grid.setColumnStretch(1, 1)
        grid.addWidget(_field_label("Percorso cartella dati"), 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        grid.addLayout(path_row, 0, 1)

        layout.addLayout(grid)
        vbox.addWidget(card)
        vbox.addStretch(1)
        self._stack.addWidget(page)
        starting_box = QWidget()
        return root_path_edit, browse_btn, starting_box

    def _build_pages(self):
        monitor_combo, debug_check, manual_start_check = self._build_page_generale()
        conn_type_combo, debounce_edit, tcp_ip_value_label, tcp_port_edit, tcp_card = self._build_page_comunicazione()
        heartbeat_interval_edit, heartbeat_max_missed_edit = self._build_page_heartbeat()
        dev_checks = self._build_page_dispositivi()
        live_check, tv_check, live_ip_edit, live_port_edit, live_box = self._build_page_live()
        root_path_edit, browse_btn, starting_box = self._build_page_cartelle()

        return (
            monitor_combo,
            debug_check,
            live_check,
            tv_check,
            manual_start_check,
            conn_type_combo,
            debounce_edit,
            heartbeat_interval_edit,
            heartbeat_max_missed_edit,
            tcp_ip_value_label,
            tcp_port_edit,
            tcp_card,
            dev_checks,
            live_ip_edit,
            live_port_edit,
            live_box,
            root_path_edit,
            browse_btn,
            starting_box,
        )
