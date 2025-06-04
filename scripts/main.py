# main.py

import sys
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from pathlib import Path
from src.config import ASSETS_DIR


def main():
    app = QApplication(sys.argv)
    
    qss_path = Path(ASSETS_DIR) / "styles.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
