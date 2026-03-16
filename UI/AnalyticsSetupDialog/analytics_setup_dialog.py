from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class AnalyticsSetupDialog(QDialog):
    """Collects track and weather context used by analytics export."""

    def __init__(
        self,
        initial_data: Optional[Dict[str, Any]] = None,
        circuits: Optional[List[Dict[str, Any]]] = None,
        session_name: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Analytics setup")
        self.setModal(True)
        self.resize(560, 520)

        data = initial_data or {}

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Dati aggiuntivi per KPI ingegneristici", self)
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        root.addWidget(title)

        subtitle = QLabel(
            "Inserisci i dati pista/meteo prima della generazione risultati analytics.",
            self,
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #5f6873;")
        root.addWidget(subtitle)

        if session_name:
            session_lbl = QLabel(f"Sessione: {session_name}", self)
            session_lbl.setStyleSheet("font-weight: 600;")
            root.addWidget(session_lbl)

        self._circuits: List[Dict[str, Any]] = list(circuits or [])

        track_group = QGroupBox("Pista", self)
        track_form = QFormLayout(track_group)

        self.circuit_combo = QComboBox(self)
        self.circuit_combo.addItem("Manual", userData=None)
        for c in self._circuits:
            cid = int(c.get("circuit_id", 0) or 0)
            name = str(c.get("name", "") or "").strip()
            loc = str(c.get("location", "") or "").strip()
            label = f"{name} ({loc})" if loc else name
            self.circuit_combo.addItem(label, userData=cid)

        selected_circuit_id = data.get("circuit_id", None)
        try:
            selected_circuit_id = int(selected_circuit_id) if selected_circuit_id is not None else None
        except Exception:
            selected_circuit_id = None

        if selected_circuit_id is not None:
            for i in range(self.circuit_combo.count()):
                if self.circuit_combo.itemData(i) == selected_circuit_id:
                    self.circuit_combo.setCurrentIndex(i)
                    break

        self.circuit_combo.currentIndexChanged.connect(self._on_circuit_changed)

        self.track_length_m = self._mk_float_spin(data.get("track_length_m", 0.0), 0.0, 50000.0, 0.1, " m")
        self.sector1_m = self._mk_float_spin(data.get("sector1_m", 0.0), 0.0, 50000.0, 0.1, " m")
        self.sector2_m = self._mk_float_spin(data.get("sector2_m", 0.0), 0.0, 50000.0, 0.1, " m")
        self.sector3_m = self._mk_float_spin(data.get("sector3_m", 0.0), 0.0, 50000.0, 0.1, " m")

        track_form.addRow("Circuito", self.circuit_combo)
        track_form.addRow("Lunghezza pista", self.track_length_m)
        track_form.addRow("Settore 1", self.sector1_m)
        track_form.addRow("Settore 2", self.sector2_m)
        track_form.addRow("Settore 3", self.sector3_m)
        root.addWidget(track_group)

        if selected_circuit_id is not None:
            self._apply_circuit_data(selected_circuit_id)

        env_group = QGroupBox("Meteo e contesto", self)
        env_form = QFormLayout(env_group)

        self.weather_state = QComboBox(self)
        self.weather_state.addItems(["dry", "wet", "mixed", "unknown"])
        self._set_combo_value(self.weather_state, str(data.get("weather_state", "unknown") or "unknown"))

        self.air_temp_c = self._mk_float_spin(data.get("air_temp_c", 0.0), -20.0, 80.0, 0.1, " C")
        self.track_temp_c = self._mk_float_spin(data.get("track_temp_c", 0.0), -20.0, 120.0, 0.1, " C")
        self.humidity_pct = self._mk_float_spin(data.get("humidity_pct", 0.0), 0.0, 100.0, 0.1, " %")
        self.wind_kmh = self._mk_float_spin(data.get("wind_kmh", 0.0), 0.0, 200.0, 0.1, " km/h")

        env_form.addRow("Stato pista", self.weather_state)
        env_form.addRow("Temperatura aria", self.air_temp_c)
        env_form.addRow("Temperatura pista", self.track_temp_c)
        env_form.addRow("Umidita", self.humidity_pct)
        env_form.addRow("Vento", self.wind_kmh)
        root.addWidget(env_group)

        notes_lbl = QLabel("Note", self)
        notes_lbl.setStyleSheet("font-weight: 600;")
        root.addWidget(notes_lbl)

        self.notes = QPlainTextEdit(self)
        self.notes.setPlaceholderText("Es. gomme, grip, eventi meteo, note strategiche...")
        self.notes.setPlainText(str(data.get("notes", "") or ""))
        self.notes.setMinimumHeight(90)
        root.addWidget(self.notes)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.buttons.button(QDialogButtonBox.Ok).setText("Conferma")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Annulla")
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

    def _mk_float_spin(self, value: Any, min_v: float, max_v: float, step: float, suffix: str) -> QDoubleSpinBox:
        w = QDoubleSpinBox(self)
        w.setDecimals(2)
        w.setMinimum(min_v)
        w.setMaximum(max_v)
        w.setSingleStep(step)
        w.setSuffix(suffix)
        try:
            w.setValue(float(value))
        except Exception:
            w.setValue(min_v)
        return w

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        idx = combo.findText(value, Qt.MatchFixedString)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentIndex(combo.count() - 1)

    def _on_accept(self) -> None:
        track_len = float(self.track_length_m.value())
        s1 = float(self.sector1_m.value())
        s2 = float(self.sector2_m.value())
        s3 = float(self.sector3_m.value())

        if track_len <= 0:
            QMessageBox.warning(self, "Dati mancanti", "Inserisci la lunghezza pista maggiore di 0.")
            self.track_length_m.setFocus()
            return

        if s1 <= 0 or s2 <= 0 or s3 <= 0:
            QMessageBox.warning(self, "Dati mancanti", "Inserisci tutte le lunghezze settore > 0.")
            return

        sectors_sum = s1 + s2 + s3
        delta = abs(sectors_sum - track_len)
        if track_len > 0 and (delta / track_len) > 0.1:
            ans = QMessageBox.question(
                self,
                "Conferma dati pista",
                "La somma dei settori differisce oltre il 10% dalla lunghezza pista. Vuoi continuare comunque?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return

        self.accept()

    def _on_circuit_changed(self, _idx: int) -> None:
        cid = self.circuit_combo.currentData()
        if cid is None:
            return
        try:
            cid = int(cid)
        except Exception:
            return
        self._apply_circuit_data(cid)

    def _apply_circuit_data(self, circuit_id: int) -> None:
        row = next((c for c in self._circuits if int(c.get("circuit_id", 0) or 0) == int(circuit_id)), None)
        if not row:
            return
        self.track_length_m.setValue(float(row.get("track_length_m", 0.0) or 0.0))
        self.sector1_m.setValue(float(row.get("sector1_m", 0.0) or 0.0))
        self.sector2_m.setValue(float(row.get("sector2_m", 0.0) or 0.0))
        self.sector3_m.setValue(float(row.get("sector3_m", 0.0) or 0.0))

    def export_payload(self) -> Dict[str, Any]:
        selected_circuit_id = self.circuit_combo.currentData()
        circuit_name = ""
        circuit_location = ""
        if selected_circuit_id is not None:
            try:
                cid = int(selected_circuit_id)
                row = next((c for c in self._circuits if int(c.get("circuit_id", 0) or 0) == cid), None)
                if row:
                    circuit_name = str(row.get("name", "") or "")
                    circuit_location = str(row.get("location", "") or "")
            except Exception:
                selected_circuit_id = None

        return {
            "circuit_id": selected_circuit_id,
            "circuit_name": circuit_name,
            "circuit_location": circuit_location,
            "track_length_m": float(self.track_length_m.value()),
            "sector1_m": float(self.sector1_m.value()),
            "sector2_m": float(self.sector2_m.value()),
            "sector3_m": float(self.sector3_m.value()),
            "weather_state": str(self.weather_state.currentText()).strip().lower(),
            "air_temp_c": float(self.air_temp_c.value()),
            "track_temp_c": float(self.track_temp_c.value()),
            "humidity_pct": float(self.humidity_pct.value()),
            "wind_kmh": float(self.wind_kmh.value()),
            "notes": self.notes.toPlainText().strip(),
        }
