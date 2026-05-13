"""Background encoding worker — converts raw.bin files to H.264 MP4 via NVENC."""
import os
import subprocess
import sys
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from imageio_ffmpeg import get_ffmpeg_exe


FFMPEG = get_ffmpeg_exe()

_STARTUPINFO = None
if sys.platform == "win32":
    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _STARTUPINFO.wShowWindow = 0


class EncodeWorker(QThread):
    progress = pyqtSignal(int, int)
    finished_all = pyqtSignal(list)

    def __init__(self, video_dir: Path, camera_names: list[str],
                 acq_type: str, w: int, h: int, fps: int, quality: int,
                 date: str, session_id: str):
        super().__init__()
        self._video_dir = video_dir
        self._camera_names = camera_names
        self._acq_type = acq_type
        self._w = w
        self._h = h
        self._fps = fps
        self._quality = quality
        self._date = date
        self._session_id = session_id

    def run(self):
        results = []
        total = len(self._camera_names)

        for i, cam in enumerate(self._camera_names):
            cam_dir = self._video_dir / cam
            raw_path = cam_dir / "raw.bin"
            if not raw_path.exists():
                results.append((cam, 0, False))
                self.progress.emit(i + 1, total)
                continue

            n_bytes = os.path.getsize(raw_path)
            n_frames = n_bytes // (self._w * self._h)

            if n_frames == 0:
                os.remove(raw_path)
                results.append((cam, 0, False))
                self.progress.emit(i + 1, total)
                continue

            mp4_name = f"{self._date}-{self._session_id}-{cam}-{self._acq_type}.mp4"
            mp4_path = cam_dir / mp4_name

            cmd = [
                FFMPEG, "-y",
                "-f", "rawvideo", "-vcodec", "rawvideo",
                "-s", f"{self._w}x{self._h}", "-pix_fmt", "gray",
                "-r", str(self._fps), "-an",
                "-i", str(raw_path),
                "-c:v", "h264_nvenc",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                "-qp", str(self._quality),
                "-bf:v", "0", "-gpu", "0",
                "-loglevel", "warning",
                str(mp4_path),
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True, startupinfo=_STARTUPINFO,
                               timeout=max(60, n_frames // 30))
                os.remove(raw_path)
                results.append((cam, n_frames, True))
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"[encode] {cam} failed: {type(e).__name__}", flush=True)
                results.append((cam, n_frames, False))

            self.progress.emit(i + 1, total)

        self.finished_all.emit(results)
