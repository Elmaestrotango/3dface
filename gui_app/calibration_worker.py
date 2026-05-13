"""Background worker for running sleap-anipose calibration via uv run."""
import subprocess
import shutil
import sys
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal


class CalibrationWorker(QThread):
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, session_dir: Path, script_path: Path):
        super().__init__()
        self._session_dir = session_dir
        self._script_path = script_path

    def run(self):
        uv = shutil.which("uv")
        if not uv:
            self.finished.emit(False, "uv not found on PATH")
            return

        if not self._script_path.exists():
            self.finished.emit(False, f"Script not found: {self._script_path}")
            return

        self.status.emit("Running calibration...")
        cmd = [uv, "run", str(self._script_path), str(self._session_dir)]

        try:
            # Show a console window so the user can see progress
            creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            result = subprocess.run(
                cmd, capture_output=False, timeout=600,
                creationflags=creationflags,
            )
            if result.returncode == 0:
                self.status.emit("Calibration complete")
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, f"Calibration failed (exit code {result.returncode})")
        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Calibration timed out (10 min)")
        except Exception as e:
            self.finished.emit(False, str(e))
