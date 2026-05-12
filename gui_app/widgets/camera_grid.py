"""2x3 camera grid display widget with per-camera FPS indicator."""
import numpy as np
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QFont


class CameraGridWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)

        self._labels: list[QLabel] = []
        self._name_overlays: list[QLabel] = []
        self._fps_overlays: list[QLabel] = []

        for i in range(6):
            container = QWidget()
            container.setStyleSheet("background-color: #0f0f1e; border: 1px solid #333; border-radius: 4px;")

            label = QLabel(container)
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumSize(320, 200)
            label.setScaledContents(True)

            name_overlay = QLabel(f"cam{i+1}", container)
            name_overlay.setFont(QFont("Segoe UI", 9))
            name_overlay.setStyleSheet("color: rgba(255,255,255,150); background: transparent; border: none; padding: 4px;")
            name_overlay.setAlignment(Qt.AlignLeft | Qt.AlignTop)

            fps_overlay = QLabel("", container)
            fps_overlay.setFont(QFont("Segoe UI", 9))
            fps_overlay.setStyleSheet("color: rgba(100,255,100,180); background: transparent; border: none; padding: 4px;")
            fps_overlay.setAlignment(Qt.AlignLeft | Qt.AlignBottom)

            row, col = divmod(i, 3)
            layout.addWidget(container, row, col)
            self._labels.append(label)
            self._name_overlays.append(name_overlay)
            self._fps_overlays.append(fps_overlay)

        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        for c in range(3):
            layout.setColumnStretch(c, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for i, label in enumerate(self._labels):
            parent = label.parent()
            w, h = parent.width(), parent.height()
            label.setGeometry(0, 0, w, h)
            self._name_overlays[i].setGeometry(0, 0, w, 28)
            self._fps_overlays[i].setGeometry(0, h - 24, w, 24)

    def update_frame(self, cam_index: int, frame: np.ndarray):
        if frame is None:
            return
        h, w = frame.shape[:2]
        qimg = QImage(frame.data, w, h, w, QImage.Format_Grayscale8)
        self._labels[cam_index].setPixmap(QPixmap.fromImage(qimg))

    def update_fps(self, cam_index: int, fps: float):
        self._fps_overlays[cam_index].setText(f"{fps:.0f} fps")
