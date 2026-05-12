"""Sidebar widget with session parameters, toggle switches, progress bar, and status."""
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QLabel,
    QProgressBar, QFrame, QPushButton, QFileDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from gui_app.widgets.toggle_switch import ToggleSwitch


class SidebarWidget(QWidget):
    calibrate_toggled = pyqtSignal(bool)
    record_toggled = pyqtSignal(bool)

    def __init__(self, default_output_dir: str = r"C:\Users\isaac\Desktop\3dpose\data", parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("Metadata")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setStyleSheet("color: #dcdcdc; border: none;")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #444;")
        layout.addWidget(sep)

        self._output_dir = default_output_dir
        self._dir_button = QPushButton(self._truncate_path(self._output_dir))
        self._dir_button.setToolTip(self._output_dir)
        self._dir_button.setStyleSheet(
            "QPushButton { background: #1a1a2e; color: #88aadd; border: 1px solid #444; "
            "border-radius: 3px; padding: 5px 8px; font-size: 10px; text-align: left; }"
            "QPushButton:hover { border-color: #5078c8; background: #222244; }"
        )
        self._dir_button.clicked.connect(self._pick_output_dir)
        layout.addWidget(self._dir_button)

        layout.addSpacing(4)

        form = QFormLayout()
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._fields: dict[str, QLineEdit] = {}
        defaults = [
            ("date", datetime.now().strftime("%Y%m%d")),
            ("mouse_1", ""),
            ("mouse_2", ""),
            ("assay", "open_field"),
            ("experimenter", "IT"),
            ("cohort", ""),
            ("cage", ""),
            ("notes", ""),
        ]
        for name, default in defaults:
            field = QLineEdit(default)
            field.setStyleSheet(
                "QLineEdit { background: #1a1a2e; color: #dcdcdc; border: 1px solid #444; "
                "border-radius: 3px; padding: 4px 6px; font-size: 11px; }"
                "QLineEdit:focus { border-color: #5078c8; }"
                "QLineEdit:read-only { background: #111122; color: #888; }"
            )
            label_text = name.replace("_", " ").title()
            label = QLabel(label_text)
            label.setStyleSheet("color: #aaa; font-size: 11px; border: none;")
            form.addRow(label, field)
            self._fields[name] = field

        layout.addLayout(form)
        layout.addSpacing(12)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #444;")
        layout.addWidget(sep2)
        layout.addSpacing(4)

        acq_label = QLabel("Acquisition")
        acq_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        acq_label.setStyleSheet("color: #dcdcdc; border: none;")
        layout.addWidget(acq_label)

        self._calibrate_toggle = ToggleSwitch("Calibrate", QColor(66, 133, 244))
        self._record_toggle = ToggleSwitch("Record", QColor(234, 67, 53))
        self._calibrate_toggle.toggled.connect(self._on_calibrate)
        self._record_toggle.toggled.connect(self._on_record)
        layout.addWidget(self._calibrate_toggle)
        layout.addWidget(self._record_toggle)

        layout.addSpacing(8)

        self._progress = QProgressBar()
        self._progress.setStyleSheet(
            "QProgressBar { background: #1a1a2e; border: 1px solid #444; border-radius: 3px; "
            "text-align: center; color: #dcdcdc; font-size: 10px; height: 18px; }"
            "QProgressBar::chunk { background: #ffaa00; border-radius: 2px; }"
        )
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        layout.addStretch()

        self._status = QLabel("IDLE")
        self._status.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._status.setStyleSheet("color: #888; border: none; padding: 4px;")
        layout.addWidget(self._status)

    def _truncate_path(self, path: str, max_len: int = 32) -> str:
        if len(path) <= max_len:
            return path
        parts = Path(path).parts
        return str(Path(parts[0], "...", *parts[-2:]))

    def _pick_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory", self._output_dir)
        if d:
            self._output_dir = d
            self._dir_button.setText(self._truncate_path(d))
            self._dir_button.setToolTip(d)

    @property
    def output_dir(self) -> str:
        return self._output_dir

    def _on_calibrate(self, checked):
        if checked:
            self._record_toggle.setEnabled(False)
        else:
            self._record_toggle.setEnabled(True)
        self.calibrate_toggled.emit(checked)

    def _on_record(self, checked):
        if checked:
            self._calibrate_toggle.setEnabled(False)
        else:
            self._calibrate_toggle.setEnabled(True)
        self.record_toggled.emit(checked)

    def get_field_values(self) -> dict:
        return {k: v.text() for k, v in self._fields.items()}

    def set_fields_editable(self, editable: bool):
        for field in self._fields.values():
            field.setReadOnly(not editable)
        self._dir_button.setEnabled(editable)

    def set_status(self, text: str, color: str):
        self._status.setText(text)
        self._status.setStyleSheet(f"color: {color}; border: none; padding: 4px;")

    def show_progress(self, current: int, total: int):
        self._progress.setVisible(True)
        self._progress.setMaximum(total)
        self._progress.setValue(current)
        self._progress.setFormat(f"Encoding {current}/{total}")

    def hide_progress(self):
        self._progress.setVisible(False)
        self._progress.setValue(0)

    def set_toggles_enabled(self, enabled: bool):
        self._calibrate_toggle.setEnabled(enabled)
        self._record_toggle.setEnabled(enabled)

    def reset_toggles(self):
        self._calibrate_toggle.setChecked(False)
        self._record_toggle.setChecked(False)
        self._calibrate_toggle.setEnabled(True)
        self._record_toggle.setEnabled(True)
