# Updated main_window.py and home_page.py to include counties handling

# main_window.py
import sys
import ctypes
import threading
import traceback
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QMessageBox,
)
import pandas as pd

from src.config import ensure_dirs_exist, LOG_FILE, ASSETS_DIR, OUTPUT_DIR
from scraper.logging_config import configure_logging
from scraper.runner import run_scraping
from ui.pages.home_page import HomePage
from ui.pages.run_page import RunPage
from ui.pages.status_page import StatusPage
from persistence.average_time_manager import load_averages, update_averages as persist_update_averages


class ScrapeWorker(QThread):
    log_line = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, states: list[str], keywords: list[str], counties: dict[str, list[str]] | None = None):
        super().__init__()
        self.states = states
        self.keywords = keywords
        self.counties = counties or {}
        self._cancel_event = threading.Event()

    def run(self):
        try:
            state_to_df, county_to_df, cache_path, state_durations, county_durations = run_scraping(
                self.states,
                self.keywords,
                counties=self.counties,
                cancel_event=self._cancel_event
            )
            state_to_df['_output_file'] = cache_path

            self.log_line.emit(f"✅ saved output to: {cache_path.name}")
            self.finished.emit({
                "success": True,
                "results": state_to_df,
                "county_results": county_to_df,
                "timings": {**state_durations, **county_durations},
            })
        except RuntimeError as e:
            msg = str(e)
            self.log_line.emit(msg)
            # failure map
            results = {state: pd.DataFrame([{"success": False}]) for state in self.states}
            results['_error'] = msg
            self.finished.emit({"success": False, "results": results})
        except Exception as exc:
            tb = traceback.format_exc()
            self.log_line.emit(f"unexpected error: {exc}")
            self.log_line.emit(tb)
            results = {state: pd.DataFrame([{"success": False}]) for state in self.states}
            results['_error'] = f"{exc}"
            self.finished.emit({"success": False, "results": results})

    def cancel(self):
        self._cancel_event.set()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_dirs_exist()
        configure_logging(LOG_FILE)
        if sys.platform == "win32":
            myappid = 'com.hotb.rfpscraper.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        self.setWindowTitle("RFP Scraper")
        self.setWindowIcon(QIcon(str(Path(ASSETS_DIR) / "hotb_logo_square.png")))
        from src.ui.ui_scale import px
        self.resize(px(1440), px(900))
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home_page = HomePage()
        self.run_page = RunPage()
        self.status_page = StatusPage()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.run_page)
        self.stack.addWidget(self.status_page)

        self._worker: ScrapeWorker | None = None
        self._canceled = False

        # Updated signal to include counties
        self.home_page.start_run.connect(self.on_start_run)
        self.run_page.cancel_run.connect(self.on_cancel_run)
        self.status_page.back_to_home.connect(self.on_back_to_home)

    def on_start_run(self, keywords: str, states: list[str], counties: dict[str, list[str]]):
        if not states:
            QMessageBox.warning(self, "No States Selected", "please select at least one state.")
            return
        keyword_list = [line.strip() for line in keywords.splitlines() if line.strip()]
        self._canceled = False
        self.run_page.start_scraper(keywords, states)
        self.stack.setCurrentWidget(self.run_page)
        # Pass counties (empty for now)
        self._worker = ScrapeWorker(states, keyword_list, counties)
        self._worker.log_line.connect(self.run_page.append_log)
        self._worker.finished.connect(self.on_run_finished)
        self._worker.start()

    def on_cancel_run(self):
        if self._worker:
            self._worker.cancel()
        self._canceled = True
        self.run_page.stop_tailing()
        self.run_page.log_output.clear()
        self.run_page.cancel_button.setEnabled(True)

    def on_run_finished(self, payload: dict):
        self.run_page.stop_tailing()
        self.home_page.run_button.setEnabled(True)
        if self._canceled:
            self._worker = None
            self.stack.setCurrentWidget(self.home_page)
            return
        results = payload.get("results", {})
        state_timings = payload.get("timings", {})
        if state_timings:
            avg_data = load_averages()
            persist_update_averages(avg_data, state_timings)
        self.status_page.display_results(results)
        self.stack.setCurrentWidget(self.status_page)
        import os, platform
        desktop_path = OUTPUT_DIR / "rfp_scraping_output.xlsx"
        if desktop_path.exists():
            if platform.system() == "Windows":
                os.startfile(desktop_path)
            elif platform.system() == "Darwin":
                os.system(f"open \"{desktop_path}\"")
            else:
                os.system(f"xdg-open \"{desktop_path}\"")
        self._worker = None

    def on_back_to_home(self):
        self.run_page.cancel_button.setEnabled(True)
        self.run_page.log_output.clear()
        self.stack.setCurrentWidget(self.home_page)