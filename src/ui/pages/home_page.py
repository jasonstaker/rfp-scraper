# src/ui/pages/home_page.py

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal


class HomePage(QWidget):
    # Signal: emits (keywords: str, states: list[str])
    start_run = pyqtSignal(str, list)

    def __init__(self):
        super().__init__()
        # TODO: add widgets (QLineEdit, QComboBox, QPushButton, etc.)
        # For now, this is just a placeholder.

    def reset_fields(self):
        """
        Called when returning to HomePage (e.g. after running).
        Should clear any inputs (keywords, state selection).
        """
        pass
