import sys

from PySide6.QtWidgets import QApplication

from co2_control_app.controller import ApplicationController
from co2_control_app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Управляющая программа для экспериментальной установки очистки воздуха")

    controller = ApplicationController()
    window = MainWindow(controller)
    window.show()

    return app.exec()
