# main_window.py

import sys
import ctypes
import threading
import traceback
from pathlib import Path
from shutil import copy2
from src.config import OUTPUT_FILENAME_PREFIX, OUTPUT_FILE_EXTENSION

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QMainWindow,
    QStackedWidget,
    QMessageBox,
    QFileDialog,
)
import pandas as pd

from src.scraper.utils.data_utils import ensure_dirs_exist
from src.config import LOG_FILE, ASSETS_DIR, OUTPUT_DIR
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
                "state_durations": state_durations,
                "county_durations": county_durations,
            })
        except RuntimeError as e:
            msg = str(e)
            self.log_line.emit(msg)
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
        self._build_menu()
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

        # connect signals with counties support
        self.home_page.start_run.connect(self.on_start_run)
        self.run_page.cancel_run.connect(self.on_cancel_run)
        self.status_page.back_to_home.connect(self.on_back_to_home)

    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        download_action = file_menu.addAction("Download &Log…")
        download_action.setStatusTip("Save a copy of the current log file")
        download_action.triggered.connect(self._download_log)

        file_menu.addSeparator()
        quit_action = file_menu.addAction("&Quit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

    def _download_log(self):

        # suggest the current log filename
        src = Path(LOG_FILE)
        if not src.exists():
            QMessageBox.warning(self, "No Log File", f"Log file not found:\n{src}")
            return

        # ask where to save it
        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Log As…",
            str(src.name),
            "Log files (*.log);;All files (*.*)"
        )
        if not dest_path:
            return  # user cancelled

        try:
            copy2(src, dest_path)
            QMessageBox.information(self, "Log Saved", f"Log successfully saved to:\n{dest_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Log", str(e))

    def on_start_run(self, keywords: str, states: list[str], counties: dict[str, list[str]]):
        # require at least one state OR one county
        has_counties = any(county_list for county_list in counties.values())
        if not states and not has_counties:
            QMessageBox.warning(
                self,
                "No States/Counties Selected",
                "Please select at least one state or county."
            )
            return

        keyword_list = [line.strip() for line in keywords.splitlines() if line.strip()]
        self._canceled = False
        self.run_page.start_scraper(keywords, states, counties)
        self.stack.setCurrentWidget(self.run_page)
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
        state_durs  = payload.get("state_durations", {})
        county_durs = payload.get("county_durations", {})
        if state_durs or county_durs:
            avg_data = load_averages()
            persist_update_averages(avg_data, state_durs, county_durs)
        state_results  = payload.get("results", {})
        county_results = payload.get("county_results", {})
        self.status_page.display_results(state_results, county_results)
        self.stack.setCurrentWidget(self.status_page)
        import os, platform
        desktop_path = OUTPUT_DIR / f"{OUTPUT_FILENAME_PREFIX}{OUTPUT_FILE_EXTENSION}"
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
