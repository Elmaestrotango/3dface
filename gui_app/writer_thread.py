"""Per-camera raw binary writer thread."""
import os
import time
from collections import deque
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal


class WriterThread(QThread):
    frames_written = pyqtSignal(int, int)

    def __init__(self, cam_index: int, raw_path: Path, write_queue: deque):
        super().__init__()
        self._cam_index = cam_index
        self._raw_path = str(raw_path)
        self._write_queue = write_queue
        self._running = False

    def run(self):
        self._running = True
        fd = os.open(self._raw_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_BINARY)
        count = 0
        try:
            while self._running or self._write_queue:
                if self._write_queue:
                    os.write(fd, self._write_queue.popleft())
                    count += 1
                else:
                    time.sleep(0.001)
        finally:
            os.close(fd)
        self.frames_written.emit(self._cam_index, count)

    def stop(self):
        self._running = False
