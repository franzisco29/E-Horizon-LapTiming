from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QTableWidget


# =========================
# COLORI BASE
# =========================

PASSED_COLOR = QColor(255, 255, 134)     # Giallino passaggio
POLE_COLOR = QColor(153, 102, 204)       # Viola Best Lap / Leader
END_COLOR = QColor(84, 84, 84)           # Grigio fine gara
SWAP_COLOR = QColor(30, 144, 255)        # Blu cambio pilota

# Bandiere
GREEN_FLAG = QColor("green")
YELLOW_FLAG = QColor("yellow")
RED_FLAG = QColor("red")
BLUE_FLAG = QColor("blue")
CLEAR_FLAG = QColor("transparent")


# =========================
# UTILITY BASE
# =========================

def _apply_row_style(table: QTableWidget, row: int, back: QColor, fore: QColor) -> None:
    """Applica background/foreground a tutta la riga."""
    for col in range(table.columnCount()):
        item = table.item(row, col)
        if item:
            item.setBackground(QBrush(back))
            item.setForeground(QBrush(fore))


def _reset_row_to_default(table: QTableWidget, row: int) -> None:
    """
    Ripristina i colori di default del tema.
    NON usare bianco/nero fisso.
    """
    empty = QBrush()
    for col in range(table.columnCount()):
        item = table.item(row, col)
        if item:
            item.setBackground(empty)
            item.setForeground(empty)


# =========================
# PASS COLOR
# =========================

def set_pass_color(table: QTableWidget, row_index: int, swap: bool, best_lap_row: int) -> None:
    """
    Evidenzia temporaneamente una riga al passaggio del transponder.
    Poi ripristina il colore originale del tema.
    """
    if row_index < 0 or row_index >= table.rowCount():
        return

    delay = 500

    if swap:
        _apply_row_style(table, row_index, SWAP_COLOR, QColor("white"))
        delay = 1000
    else:
        if row_index == 0:
            _apply_row_style(table, row_index, POLE_COLOR, QColor("white"))
            delay = 1000
        else:
            _apply_row_style(table, row_index, PASSED_COLOR, QColor("black"))
            delay = 500

    def _restore():
        if row_index < table.rowCount():
            _reset_row_to_default(table, row_index)

            # Riapplica best lap se necessario
            if 0 <= best_lap_row < table.rowCount():
                set_best_lap_cell(table, best_lap_row)

        table.viewport().update()

    QTimer.singleShot(delay, _restore)


# =========================
# BEST LAP
# =========================

def set_best_lap_cell(table: QTableWidget, row: int) -> None:
    """
    Evidenzia in viola la cella Best Lap (colonna 11).
    NON altera il background della riga.
    """
    if 0 <= row < table.rowCount():
        item = table.item(row, 11)
        if item:
            item.setForeground(QBrush(POLE_COLOR))


# =========================
# END RACE
# =========================

def set_end(table: QTableWidget, row: int) -> None:
    """Colora la riga di grigio (fine gara)."""
    if 0 <= row < table.rowCount():
        _apply_row_style(table, row, END_COLOR, QColor("white"))


# =========================
# RESET COMPLETO
# =========================

def reset_all_colors(table: QTableWidget) -> None:
    """
    Reset totale della tabella al colore di default del tema.
    NON bianco fisso.
    """
    for r in range(table.rowCount()):
        _reset_row_to_default(table, r)

    table.viewport().update()