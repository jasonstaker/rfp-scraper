# src/ui/pages/run_page.py

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal


class RunPage(QWidget):
    # Signal: emitted when user clicks “Cancel”
    cancel_run = pyqtSignal()

    def __init__(self):
        super().__init__()
        # TODO: add widgets (e.g. a log QTextEdit/QPlainTextEdit and a Cancel QPushButton)
        # For now, this is just a placeholder.

        # Placeholders so MainWindow can connect to these attributes:
        self.log_output = None       # will become a QTextEdit/QPlainTextEdit
        self.cancel_button = None    # will become a QPushButton

    def append_log(self, text: str):
        """
        Called by ScrapeWorker to append a log line into the UI.
        """
        pass

    def start_scraper(self, keywords: str, states: list):
        """
        Called by MainWindow to kick off the scraping process.
        Should start a QThread or worker internally and connect its signals.
        """
        pass
