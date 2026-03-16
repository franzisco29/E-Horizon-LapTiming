from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QAbstractItemView,
	QDialogButtonBox,
	QHeaderView,
	QLabel,
	QTableWidget,
	QVBoxLayout,
	QWidget,
)


@dataclass(slots=True)
class ResultPreviewWindowRefs:
	title_label: QLabel
	subtitle_label: QLabel
	table: QTableWidget
	buttons: QDialogButtonBox


def build_result_preview_ui(parent: QWidget) -> tuple[QWidget, ResultPreviewWindowRefs]:
	root = QWidget(parent)
	lay = QVBoxLayout(root)
	lay.setContentsMargins(12, 12, 12, 12)
	lay.setSpacing(8)

	title_label = QLabel("Preview risultati con penalita", root)
	title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
	lay.addWidget(title_label)

	subtitle_label = QLabel(
		"Aggiungi/rimuovi penalita per pilota. Nessuna modifica al modello live finche non confermi.",
		root,
	)
	subtitle_label.setWordWrap(True)
	subtitle_label.setStyleSheet("color: #60666f;")
	lay.addWidget(subtitle_label)

	table = QTableWidget(root)
	table.setColumnCount(12)
	table.setHorizontalHeaderLabels(
		[
			"Pos",
			"Pilota",
			"Team",
			"Giri",
			"Tempo Base",
			"Penalita",
			"Media Giro",
			"Conversione Giri",
			"Tempo Corretto",
			"Status",
			"Punti",
			"Azioni",
		]
	)
	table.setEditTriggers(QAbstractItemView.NoEditTriggers)
	table.setSelectionBehavior(QAbstractItemView.SelectRows)
	table.setSelectionMode(QAbstractItemView.SingleSelection)
	table.verticalHeader().setVisible(False)
	table.setAlternatingRowColors(True)

	hdr = table.horizontalHeader()
	hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
	hdr.setSectionResizeMode(1, QHeaderView.Stretch)
	hdr.setSectionResizeMode(2, QHeaderView.Stretch)
	hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
	hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
	hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
	hdr.setSectionResizeMode(6, QHeaderView.ResizeToContents)
	hdr.setSectionResizeMode(7, QHeaderView.ResizeToContents)
	hdr.setSectionResizeMode(8, QHeaderView.ResizeToContents)
	hdr.setSectionResizeMode(9, QHeaderView.ResizeToContents)
	hdr.setSectionResizeMode(10, QHeaderView.ResizeToContents)
	hdr.setSectionResizeMode(11, QHeaderView.ResizeToContents)

	lay.addWidget(table, 1)

	buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, root)
	buttons.button(QDialogButtonBox.Ok).setText("Applica e genera PDF")
	buttons.button(QDialogButtonBox.Cancel).setText("Annulla")
	lay.addWidget(buttons)

	return root, ResultPreviewWindowRefs(
		title_label=title_label,
		subtitle_label=subtitle_label,
		table=table,
		buttons=buttons,
	)

