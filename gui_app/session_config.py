"""Session configuration and path management."""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class SessionConfig:
    date: str = ""
    mouse_1: str = ""
    mouse_2: str = ""
    assay: str = "open_field"
    experimenter: str = "IT"
    cohort: str = ""
    cage: str = ""
    notes: str = ""

    base_data_dir: Path = Path(r"C:\Users\isaac\Desktop\3dpose\data")
    pfs_path: Path = Path(r"C:\Users\isaac\Desktop\3dpose\data\configs\mono8_1920x1200.pfs")
    serial_port: str = "COM3"
    trigger_pins: list = field(default_factory=lambda: [2, 4, 6, 8, 10, 12])
    frame_rate: int = 100
    frame_width: int = 1920
    frame_height: int = 1200
    camera_names: list = field(default_factory=lambda: ["cam1", "cam2", "cam3", "cam4", "cam5", "cam6"])
    quality: int = 21

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%Y%m%d")
        if not self.mouse_1:
            self.mouse_1 = "m1"
        if not self.mouse_2:
            self.mouse_2 = "m2"

    @property
    def session_id(self) -> str:
        return f"{self.mouse_1}_{self.mouse_2}"

    @property
    def session_dir(self) -> Path:
        return self.base_data_dir / self.date / self.session_id

    def video_dir(self, acq_type: str) -> Path:
        return self.session_dir / acq_type

    def video_filename(self, cam: str, acq_type: str) -> str:
        return f"{self.date}-{self.session_id}-{cam}-{acq_type}.mp4"

    def ensure_dirs(self, acq_type: str):
        d = self.video_dir(acq_type)
        for cam in self.camera_names:
            (d / cam).mkdir(parents=True, exist_ok=True)
        return d

    def save_metadata(self):
        meta = dict(
            date=self.date, session_id=self.session_id,
            mouse_1=self.mouse_1, mouse_2=self.mouse_2,
            assay=self.assay, cohort=self.cohort, cage=self.cage,
            experimenter=self.experimenter, notes=self.notes,
            num_cameras=len(self.camera_names), camera_names=self.camera_names,
            frame_rate=self.frame_rate, resolution=[self.frame_width, self.frame_height],
        )
        self.session_dir.mkdir(parents=True, exist_ok=True)
        path = self.session_dir / "session_metadata.json"
        with open(path, "w") as f:
            json.dump(meta, f, indent=2)
        return path
