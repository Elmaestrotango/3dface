"""Per-camera grab thread — grabs frames, writes raw to disk, provides display thumbnails."""
import os
import time
import numpy as np
from collections import deque
from pathlib import Path
from PyQt5.QtCore import QThread
import pypylon.pylon as pylon


class GrabThread(QThread):
    def __init__(self, cam_index: int, camera: pylon.InstantCamera,
                 raw_path: Path = None, display_every: int = 1,
                 downsample: int = 6):
        super().__init__()
        self._cam_index = cam_index
        self._camera = camera
        self._raw_path = raw_path
        self._display_every = display_every
        self._downsample = downsample
        self._running = False
        self._triggers_stopped = False
        self.frame_count = 0
        self.timestamps = []
        self.latest_frame = None
        self.current_fps = 0.0
        self._fps_times = deque(maxlen=10)

    def run(self):
        self._running = True
        self._triggers_stopped = False
        self.frame_count = 0
        self.timestamps = []
        recording = self._raw_path is not None
        fd = None

        if recording:
            fd = os.open(str(self._raw_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_BINARY)

        self._camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
        frame_n = 0

        try:
            while self._running and self._camera.IsGrabbing():
                try:
                    timeout = 200 if (recording and self._triggers_stopped) else (200 if recording else 2000)
                    result = self._camera.RetrieveResult(timeout, pylon.TimeoutHandling_ThrowException)
                    if not result.GrabSucceeded():
                        result.Release()
                        continue

                    img = result.Array

                    if recording:
                        os.write(fd, img)
                        self.frame_count += 1
                        self.timestamps.append(result.TimeStamp * 1e-9)

                    frame_n += 1
                    now = time.perf_counter()
                    self._fps_times.append(now)
                    if len(self._fps_times) >= 2:
                        dt = self._fps_times[-1] - self._fps_times[0]
                        if dt > 0:
                            self.current_fps = (len(self._fps_times) - 1) / dt

                    if frame_n % self._display_every == 0:
                        d = self._downsample
                        self.latest_frame = img[::d, ::d].copy()

                    result.Release()

                except pylon.TimeoutException:
                    if recording and self._triggers_stopped:
                        break
                    if not self._running:
                        break
                except Exception:
                    if not self._running:
                        break
                    time.sleep(0.001)
        finally:
            if fd is not None:
                os.close(fd)
            try:
                self._camera.StopGrabbing()
            except Exception:
                pass

    def signal_triggers_stopped(self):
        self._triggers_stopped = True

    def stop(self):
        self._running = False
