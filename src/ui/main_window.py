# src/ui/main_window.py

import sys
import threading
import traceback
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QMessageBox,
)

from src.config import ensure_dirs_exist, LOG_FILE, CACHE_DIR
from scraper.logging_config import configure_logging
from scraper.runner import run_scraping
#from ui.common import load_icon
from ui.pages.home_page import HomePage
from ui.pages.run_page import RunPage
from ui.pages.status_page import StatusPage


class ScrapeWorker(QThread):
    log_line = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, states: list[str]):
        super().__init__()
        self.states = states
        self._cancel_event = threading.Event()

    def run(self):
        try:
            # emit a preliminary log line
            self.log_line.emit(f"[{', '.join(self.states)}] Beginning scrape…")

            # call the runner, passing the cancel_event
            cache_path = run_scraping(self.states, cancel_event=self._cancel_event)

            # on success, build a simple results dict
            results = {state: True for state in self.states}
            results["_output_file"] = cache_path
            self.log_line.emit(f"✅ Saved output to: {cache_path.name}")

            self.finished.emit({"success": True, "results": results})

        except RuntimeError as cancel_or_nodata:
            # raised if user canceled or no records scraped
            msg = str(cancel_or_nodata)
            self.log_line.emit(f"🛑 {msg}")

            # mark every requested state as False, include the error message
            results = {state: False for state in self.states}
            results["_error"] = msg
            self.finished.emit({"success": False, "results": results})

        except Exception as exc:
            # catch any unexpected exception
            tb = traceback.format_exc()
            self.log_line.emit(f"❌ Unexpected error: {exc}")
            self.log_line.emit(tb)

            results = {state: False for state in self.states}
            results["_error"] = f"{exc}"
            self.finished.emit({"success": False, "results": results})

    def cancel(self):
        self._cancel_event.set()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # ensure that output/, cache/, persistence/ directories exist
        ensure_dirs_exist()

        # configure logging into LOG_FILE
        configure_logging(LOG_FILE)

        self.setWindowTitle("RFP Scraper GUI")
        self.setWindowIcon(load_icon("hotb_logo.jpg"))
        self.resize(600, 400)

        # central widget: a QStackedWidget that holds Home, Run, Status pages
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # instantiate each page
        self.home_page = HomePage()
        self.run_page = RunPage()
        self.status_page = StatusPage()

        # add pages to the stack (index 0: Home, 1: Run, 2: Status)
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.run_page)
        self.stack.addWidget(self.status_page)

        # keep a reference to the current ScrapeWorker
        self._worker: ScrapeWorker | None = None

        # wire signals:
        self.home_page.start_run.connect(self.on_start_run)
        self.run_page.cancel_run.connect(self.on_cancel_run)
        self.status_page.back_to_home.connect(self.on_back_to_home)

    def on_start_run(self, keywords: str, states: list[str]):
        if not states:
            QMessageBox.warning(self, "No States Selected", "Please select at least one state.")
            return

        # clear any previous run logs
        self.run_page.log_output.clear()

        # switch to the RunPage
        self.stack.setCurrentWidget(self.run_page)

        # instantiate and start the background worker
        self._worker = ScrapeWorker(states)
        self._worker.log_line.connect(self.run_page.append_log)
        self._worker.finished.connect(self.on_run_finished)
        self._worker.start()

    def on_cancel_run(self):
        if self._worker:
            self._worker.cancel()
            self.run_page.cancel_button.setEnabled(False)
            self.run_page.append_log("Cancel requested… waiting for current attempt to end.")

    def on_run_finished(self, payload: dict):
        results = payload.get("results", {})
        self.status_page.display_results(results)
        self.stack.setCurrentWidget(self.status_page)

        # clean up worker reference
        self._worker = None

    def on_back_to_home(self):
        self.home_page.reset_fields()
        self.run_page.cancel_button.setEnabled(True)
        self.run_page.log_output.clear()
        self.stack.setCurrentWidget(self.home_page)