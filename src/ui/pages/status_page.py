# src/ui/pages/status_page.py

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal


class StatusPage(QWidget):
    # Signal: emitted when user clicks “Back to Home”
    back_to_home = pyqtSignal()

    def __init__(self):
        super().__init__()
        # TODO: add widgets (e.g. a QTableWidget or QListWidget and a Back QPushButton)
        # For now, this is just a placeholder.

    def display_results(self, results: dict):
        """
        Called by MainWindow once scraping finishes (success or failure).
        'results' will be a dict mapping state -> bool, possibly with "_error" or "_output_file".
        Populate the UI (table/list) accordingly.
        """
        pass
