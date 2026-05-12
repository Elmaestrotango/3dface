"""Main application window — wires cameras, sidebar, state machine, and encoding."""
import numpy as np
from enum import Enum
from pathlib import Path

from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPalette, QColor

from gui_app.camera_manager import CameraManager
from gui_app.serial_controller import TeensyController
from gui_app.encode_worker import EncodeWorker
from gui_app.session_config import SessionConfig
from gui_app.widgets.camera_grid import CameraGridWidget
from gui_app.widgets.sidebar import SidebarWidget


class State(Enum):
    IDLE = "IDLE"
    CALIBRATING = "CALIBRATING"
    RECORDING = "RECORDING"
    ENCODING = "ENCODING"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3DPose Acquisition")
        self.setMinimumSize(1280, 540)
        self._apply_theme()

        self._state = State.IDLE
        self._acq_type = ""
        self._encode_worker: EncodeWorker | None = None
        self._config: SessionConfig | None = None
        self._video_dir: Path | None = None

        self._camera_mgr = CameraManager()
        self._teensy = TeensyController()

        self._camera_grid = CameraGridWidget()
        self._sidebar = SidebarWidget()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._camera_grid, stretch=3)

        sidebar_container = QWidget()
        sidebar_container.setStyleSheet("background-color: #141428; border-left: 1px solid #333;")
        sidebar_layout = QHBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(self._sidebar)
        layout.addWidget(sidebar_container, stretch=0)

        self.setCentralWidget(central)

        self._sidebar.calibrate_toggled.connect(self._on_calibrate_toggle)
        self._sidebar.record_toggled.connect(self._on_record_toggle)
        self._camera_mgr.error.connect(self._on_camera_error)

        self._display_timer = QTimer()
        self._display_timer.timeout.connect(self._refresh_displays)
        self._display_timer.start(33)

        pfs = str(SessionConfig().pfs_path)
        if not self._camera_mgr.open_all(pfs):
            QTimer.singleShot(100, lambda: QMessageBox.warning(
                self, "Camera Error", "Could not open all 6 cameras. Check connections."))

        self._sidebar.set_status("IDLE", "#888")

    def _apply_theme(self):
        app = QApplication.instance()
        app.setStyle("Fusion")
        p = QPalette()
        p.setColor(QPalette.Window, QColor(25, 25, 42))
        p.setColor(QPalette.WindowText, QColor(220, 220, 220))
        p.setColor(QPalette.Base, QColor(15, 15, 30))
        p.setColor(QPalette.AlternateBase, QColor(35, 35, 55))
        p.setColor(QPalette.Text, QColor(220, 220, 220))
        p.setColor(QPalette.Button, QColor(40, 40, 65))
        p.setColor(QPalette.ButtonText, QColor(220, 220, 220))
        p.setColor(QPalette.Highlight, QColor(80, 120, 200))
        p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        p.setColor(QPalette.ToolTipBase, QColor(40, 40, 65))
        p.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
        app.setPalette(p)

    def _refresh_displays(self):
        self._display_tick = getattr(self, '_display_tick', 0) + 1
        for i, frame in enumerate(self._camera_mgr.latest_frames):
            if frame is not None:
                self._camera_grid.update_frame(i, frame)
        if self._display_tick % 10 == 0:
            for i, fps in enumerate(self._camera_mgr.current_fps):
                self._camera_grid.update_fps(i, fps)

    def _build_config(self) -> SessionConfig:
        vals = self._sidebar.get_field_values()
        return SessionConfig(
            date=vals["date"],
            mouse_1=vals["mouse_1"],
            mouse_2=vals["mouse_2"],
            assay=vals["assay"],
            experimenter=vals["experimenter"],
            cohort=vals["cohort"],
            cage=vals["cage"],
            notes=vals["notes"],
            base_data_dir=Path(self._sidebar.output_dir),
        )

    def _on_calibrate_toggle(self, checked):
        if checked:
            self._start_acquisition("calibration")
        elif self._state == State.CALIBRATING:
            self._stop_acquisition()

    def _on_record_toggle(self, checked):
        if checked:
            self._start_acquisition("recording")
        elif self._state == State.RECORDING:
            self._stop_acquisition()

    def _start_acquisition(self, acq_type: str):
        self._config = self._build_config()
        self._acq_type = acq_type
        video_dir = self._config.video_dir(acq_type)

        if video_dir.exists() and any(video_dir.rglob("*.mp4")):
            reply = QMessageBox.question(
                self, "Overwrite?",
                f"Existing files found in:\n{video_dir}\n\nOverwrite?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply == QMessageBox.No:
                self._sidebar.reset_toggles()
                return

        self._video_dir = self._config.ensure_dirs(acq_type)

        raw_paths = [
            self._video_dir / cam / "raw.bin"
            for cam in self._config.camera_names
        ]

        self._camera_mgr.start_acquisition(raw_paths)

        if not self._teensy.open():
            self._on_camera_error("Could not open serial port")
            return
        self._teensy.start_triggers(self._config.trigger_pins, self._config.frame_rate)

        self._sidebar.set_fields_editable(False)
        if acq_type == "calibration":
            self._state = State.CALIBRATING
            self._sidebar.set_status("CALIBRATING", "#4488ff")
        else:
            self._state = State.RECORDING
            self._sidebar.set_status("RECORDING", "#ff4444")

    def _stop_acquisition(self):
        self._teensy.stop_triggers(self._config.trigger_pins)
        self._teensy.close()

        cam_results = self._camera_mgr.stop_acquisition()

        self._save_frametimes(cam_results)
        self._config.save_metadata()

        self._state = State.ENCODING
        self._sidebar.set_status("ENCODING", "#ffaa00")
        self._sidebar.set_toggles_enabled(False)

        self._encode_worker = EncodeWorker(
            self._video_dir,
            self._config.camera_names,
            self._acq_type,
            self._config.frame_width,
            self._config.frame_height,
            self._config.frame_rate,
            self._config.quality,
            self._config.date,
            self._config.session_id,
        )
        self._encode_worker.progress.connect(self._sidebar.show_progress)
        self._encode_worker.finished_all.connect(self._on_encoding_done)
        self._encode_worker.start()

    def _save_frametimes(self, cam_results: list[tuple[int, list[float]]]):
        counts = [len(ts) for _, ts in cam_results if ts]
        if not counts:
            return
        min_frames = min(counts)

        for i, (count, timestamps) in enumerate(cam_results):
            if not timestamps:
                continue
            cam = self._config.camera_names[i]
            cam_dir = self._video_dir / cam

            timestamps = timestamps[:min_frames]
            t0 = timestamps[0]
            rel_ts = [t - t0 for t in timestamps]
            frame_nums = list(range(1, min_frames + 1))

            npy_path = cam_dir / "frametimes.npy"
            np.save(npy_path, np.array([frame_nums, rel_ts]))

            raw_path = cam_dir / "raw.bin"
            if raw_path.exists():
                frame_size = self._config.frame_width * self._config.frame_height
                expected_size = min_frames * frame_size
                actual_size = raw_path.stat().st_size
                if actual_size > expected_size:
                    with open(raw_path, "r+b") as f:
                        f.truncate(expected_size)

    def _on_encoding_done(self, results):
        self._sidebar.hide_progress()
        self._sidebar.set_fields_editable(True)
        self._sidebar.reset_toggles()
        self._state = State.IDLE
        self._sidebar.set_status("IDLE", "#888")

        frame_counts = [n for _, n, ok in results if ok]
        fps_vals = []
        for cam, n_frames, ok in results:
            if not ok:
                continue
            cam_dir = self._video_dir / cam / "frametimes.npy"
            try:
                ft = np.load(cam_dir)
                duration = ft[1][-1] - ft[1][0]
                fps_vals.append(ft.shape[1] / duration if duration > 0 else 0)
            except Exception:
                fps_vals.append(0)

        avg_fps = sum(fps_vals) / len(fps_vals) if fps_vals else 0
        min_frames = min(frame_counts) if frame_counts else 0
        max_frames = max(frame_counts) if frame_counts else 0

        if min_frames == max_frames:
            count_str = str(min_frames)
        else:
            count_str = f"{min_frames}-{max_frames}"

        self.statusBar().showMessage(
            f"{self._acq_type.title()} complete: {count_str} frames, {avg_fps:.1f} fps",
            15000,
        )

    def _on_camera_error(self, msg: str):
        QMessageBox.critical(self, "Error", msg)

    def closeEvent(self, event):
        self._display_timer.stop()
        if self._state in (State.CALIBRATING, State.RECORDING):
            self._teensy.stop_triggers(self._config.trigger_pins)
            self._teensy.close()
        self._camera_mgr.close_all()
        if self._encode_worker and self._encode_worker.isRunning():
            self._encode_worker.wait(5000)
        event.accept()
