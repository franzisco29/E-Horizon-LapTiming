from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QToolButton,
)



def icon(name: str) -> QIcon:
    p = Path("resources/icons") / name
    return QIcon(str(p)) if p.exists() else QIcon()


def build_stylesheet() -> str:
    # NOTE: QLabel background transparent fix incluso
    return """
    QWidget {
        background: #060A12;
        color: rgba(255,255,255,0.92);
        font-family: "Google Sans";
        font-size: 12px;
    }

    QLabel {
        background: transparent;
    }
    QLabel#Title, QLabel#Subtitle, QLabel#SectionLabel {
        background: transparent;
    }

    QFrame#GlassCard {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255,255,255,0.08),
            stop:1 rgba(255,255,255,0.03)
        );
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 22px;
    }

    QFrame#GlowLine {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(43,183,255,0.0),
            stop:0.5 rgba(43,183,255,0.70),
            stop:1 rgba(43,183,255,0.0)
        );
        border-radius: 2px;
    }

    QLabel#Title {
        font-family: "Audiowide";
        font-size: 34px;
        letter-spacing: 2px;
        color: rgba(255,255,255,0.96);
    }

    QLabel#Subtitle {
        font-size: 12px;
        color: rgba(170,210,230,0.90);
    }

    QLabel#SectionLabel {
        font-size: 11px;
        color: rgba(255,255,255,0.70);
    }

    QPushButton {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 16px;
        padding: 12px 14px;
        text-align: left;
        font-size: 13px;
    }

    QPushButton:hover {
        border: 1px solid rgba(43,183,255,0.55);
        background: rgba(43,183,255,0.10);
    }

    QPushButton:pressed {
        background: rgba(43,183,255,0.16);
    }

    QPushButton#Primary {
        background: rgba(43,183,255,0.12);
        border: 1px solid rgba(43,183,255,0.60);
        font-weight: 600;
    }

    QToolButton#IconButton {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 10px;
        padding: 6px;
    }
    QToolButton#IconButton:hover {
        border: 1px solid rgba(43,183,255,0.55);
        background: rgba(43,183,255,0.10);
    }
    QToolButton#IconButton:pressed {
        background: rgba(43,183,255,0.16);
    }
    """


# ----------------------------
# UI dataclass
# ----------------------------
@dataclass
class HomeWindowUI:
    root: QWidget

    # widgets accessibili dal backend
    bt_settings_small: QToolButton
    bt_race_manager: QPushButton
    bt_driver_manager: QPushButton
    bt_circuits: QPushButton
    bt_grid: QPushButton
    bt_new_list: QPushButton
    bt_roadsters: QPushButton

    @staticmethod
    def build() -> "HomeWindowUI":
        #load_fonts()

        root = QWidget()
        root.setWindowTitle("E-Horizon • Race Manager")
        root.setMinimumSize(980, 520)
        root.setStyleSheet(build_stylesheet())

        outer = QVBoxLayout(root)
        outer.setContentsMargins(34, 28, 34, 28)
        outer.setSpacing(18)

        # --- Top glass card ---
        card = QFrame()
        card.setObjectName("GlassCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        top_row.addStretch(1)

        bt_settings_small = QToolButton()
        bt_settings_small.setObjectName("IconButton")
        bt_settings_small.setIcon(icon("settings.svg"))
        bt_settings_small.setToolTip("Settings")
        bt_settings_small.setCursor(Qt.PointingHandCursor)
        bt_settings_small.setIconSize(QSize(18, 18))
        top_row.addWidget(bt_settings_small)

        card_layout.addLayout(top_row)

        title = QLabel("E-HORIZON")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        title.setAutoFillBackground(False)

        subtitle = QLabel("RACE MANAGER • LapTiming • Results • Control")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setAutoFillBackground(False)

        glow = QFrame()
        glow.setObjectName("GlowLine")
        glow.setFixedHeight(4)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(glow)

        outer.addWidget(card)

        # --- Buttons area ---
        label = QLabel("Quick Actions")
        label.setObjectName("SectionLabel")
        outer.addWidget(label)

        actions_grid = QGridLayout()
        actions_grid.setHorizontalSpacing(14)
        actions_grid.setVerticalSpacing(12)

        bt_race_manager = QPushButton("Race Manager")
        bt_race_manager.setObjectName("Primary")
        bt_race_manager.setIcon(icon("flag.svg"))
        bt_race_manager.setMinimumHeight(48)

        bt_driver_manager = QPushButton("Piloti (Crea / Modifica)")
        bt_driver_manager.setIcon(icon("driver.svg"))
        bt_driver_manager.setMinimumHeight(48)

        bt_circuits = QPushButton("Circuiti")
        bt_circuits.setIcon(icon("circuit.svg"))
        bt_circuits.setMinimumHeight(48)

        bt_grid = QPushButton("Grid Preview")
        bt_grid.setIcon(icon("grid.svg"))
        bt_grid.setMinimumHeight(48)

        bt_new_list = QPushButton("Race Lists")
        bt_new_list.setIcon(icon("list.svg"))
        bt_new_list.setMinimumHeight(48)

        bt_roadsters = QPushButton("Roadsters")
        bt_roadsters.setIcon(icon("roster.svg"))
        bt_roadsters.setMinimumHeight(48)

        actions_grid.addWidget(bt_race_manager, 0, 0)
        actions_grid.addWidget(bt_new_list, 0, 1)
        actions_grid.addWidget(bt_driver_manager, 1, 0)
        actions_grid.addWidget(bt_roadsters, 1, 1)
        actions_grid.addWidget(bt_circuits, 2, 0)
        actions_grid.addWidget(bt_grid, 2, 1)

        actions_grid.setColumnStretch(0, 1)
        actions_grid.setColumnStretch(1, 1)

        outer.addLayout(actions_grid, 1)

        return HomeWindowUI(
            root=root,
            bt_settings_small=bt_settings_small,
            bt_race_manager=bt_race_manager,
            bt_driver_manager=bt_driver_manager,
            bt_circuits=bt_circuits,
            bt_grid=bt_grid,
            bt_new_list=bt_new_list,
            bt_roadsters=bt_roadsters,
        )
