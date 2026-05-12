"""3DPose Acquisition GUI — launch with: conda run -n 3dpose python gui.py"""
import sys
from PyQt5.QtWidgets import QApplication
from gui_app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("3DPose Acquisition")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
