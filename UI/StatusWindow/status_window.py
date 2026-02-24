from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from UI.StatusWindow.status_window_ui import StatusWindowUI


class StatusWindow(QDialog):
    """
    Porting VB StatusForm:
    - TopMost
    - no taskbar
    - 2 label: connection + status multiline
    - thread-safe update via Qt signals
    """

    # thread-safe signals
    sig_set_status = Signal(list)      # List[str]
    sig_set_conn = Signal(str, int)    # ip, port

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.startup_cancelled: bool = False

        # UI inside dialog
        self.ui = StatusWindowUI(self)
        host = QVBoxLayout(self)
        host.setContentsMargins(0, 0, 0, 0)
        host.addWidget(self.ui)

        # dialog config (VB-like)
        self.setWindowTitle("Status")
        self.resize(460, 240)

        # topmost + modal-ish behavior
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.Tool, True)                 # tool window look, usually no taskbar
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # connect signals
        self.sig_set_status.connect(self._on_set_status)
        self.sig_set_conn.connect(self._on_set_conn)

    # -----------------------
    # Public API (safe to call from any thread)
    # -----------------------
    def update_status(self, status_list: List[str]) -> None:
        # thread-safe: emit -> slot runs on GUI thread
        self.sig_set_status.emit(list(status_list))

    def update_connection(self, ip: str, port: int) -> None:
        self.sig_set_conn.emit(str(ip), int(port))

    # -----------------------
    # Slots (GUI thread)
    # -----------------------
    @Slot(list)
    def _on_set_status(self, status_list: list) -> None:
        txt = "\n".join([str(x) for x in status_list])
        self.ui.refs.status_label.setText(txt)

    @Slot(str, int)
    def _on_set_conn(self, ip: str, port: int) -> None:
        self.ui.refs.conn_label.setText(f"Connect to: {ip}/{port}")

    # -----------------------
    # Close behavior
    # -----------------------
    def closeEvent(self, event) -> None:
        # VB: when closing set StartupCancelled True
        if not self.startup_cancelled:
            self.startup_cancelled = True
        super().closeEvent(event)