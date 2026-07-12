"""Application entry point for Oil Domain Finder."""

import sys

from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Oil Domain Finder")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
