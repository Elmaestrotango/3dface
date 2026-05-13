"""Panopticon Acquisition GUI — launch with: conda run -n 3dpose python gui.py"""
import sys

from PyQt5.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap


def make_splash():
    px = QPixmap(360, 120)
    px.fill(QColor(25, 25, 42))
    p = QPainter(px)
    p.setPen(QColor(220, 220, 220))
    p.setFont(QFont("Segoe UI", 18, QFont.Bold))
    p.drawText(px.rect(), Qt.AlignCenter, "Panopticon")
    p.setPen(QColor(120, 120, 160))
    p.setFont(QFont("Segoe UI", 10))
    p.drawText(px.rect().adjusted(0, 40, 0, 0), Qt.AlignCenter, "Loading cameras...")
    p.end()
    return px


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Panopticon Acquisition")

    splash = QSplashScreen(make_splash())
    splash.show()
    app.processEvents()

    from gui_app.main_window import MainWindow
    window = MainWindow()
    window.show()
    splash.finish(window)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
