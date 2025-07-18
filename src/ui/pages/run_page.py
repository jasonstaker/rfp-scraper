# run_page.py
import os
import re
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QHBoxLayout,
)

from src.config import LOG_FILE
from persistence.average_time_manager import load_averages, estimate_total_time

# page for showing scraper progress with time-left indicator
class RunPage(QWidget):
    cancel_run = pyqtSignal()
    scraper_started = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll_log_file)
        self._log_file_pos = 0

        # track scraping states/time
        self._states: list[str] = []
        self._completed_count = 0
        self._start_time: datetime | None = None
        self._total_seconds = 0
        self._last_state: str | None = None

        # UI setup
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        from src.ui.ui_scale import px
        main_layout.setContentsMargins(px(12), px(12), px(12), px(12))
        main_layout.setSpacing(px(8))

        self.info_label = QLabel("Scraper is running…")
        self.info_label.setObjectName("run_info_label")
        self.info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.info_label)

        # Time-left label
        self.time_left_label = QLabel()
        self.time_left_label.setAlignment(Qt.AlignCenter)
        self.time_left_label.setObjectName("time_left_label")
        main_layout.addWidget(self.time_left_label)

        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("log_output")
        self.log_output.setReadOnly(True)
        self.log_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.log_output)

        button_container = QWidget()
        button_container.setObjectName("run_button_container")
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)
        button_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setMinimumWidth(px(100))
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        main_layout.addWidget(button_container)
        self.cancel_button.clicked.connect(self.cancel_run.emit)

    # modifies: self 
    # effects: begin polling and initialize log position
    def start_tailing(self):
        self.scraper_started.emit()
        self._log_file_pos = os.path.getsize(LOG_FILE)
        self.log_output.clear()
        self._timer.start()

    # modifies: self 
    # effects: stop's log tailing
    def stop_tailing(self):
        if self._timer.isActive():
            self._timer.stop()

    # requires: states is a valid list of states
    # modifies: self
    # effects: begins the scraping process, loading averages, and logging
    def start_scraper(self, keywords: str, states: list[str]):
        self._states = states
        self._completed_count = 0
        self._last_state = None

        # load historical averages and estimate total time
        averages = load_averages()
        mins, secs = estimate_total_time(averages, self._states)
        self._total_seconds = mins * 60 + secs
        self._start_time = datetime.now()

        # display initial estimate
        self._update_time_left()
        main_text = f"Running Scraper..."
        self.info_label.setText(main_text)

        # begin log polling
        self.start_tailing()

    # effects: returns whatever is new in the log file 
    def _poll_log_file(self):
        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._log_file_pos)
                new_data = f.read()
                if new_data:
                    lines = new_data.splitlines()
                    for line in lines:
                        self.log_output.appendPlainText(line)
                        # detect start of each state's scrape to update progress
                        m = re.search(r"\[([^\]]+)\] Starting scrape\.\.\.", line)
                        if m and self._start_time:
                            state = m.group(1)
                            # if this isn't the very first state, mark previous complete
                            if self._last_state is not None:
                                self._completed_count += 1
                            self._last_state = state
                            self._update_time_left()
                    self._log_file_pos = f.tell()
        except Exception as e:
            self.log_output.appendPlainText(f"<error reading log file: {e}>")
            self.stop_tailing()

    # effects: calculate and display remaining time based on elapsed and completed
    def _update_time_left(self):
        if not self._start_time:
            return
        elapsed = (datetime.now() - self._start_time).total_seconds()
        remaining = max(0, self._total_seconds - elapsed)
        mins = int(remaining) // 60
        secs = int(remaining) % 60
        # update label text
        self.time_left_label.setText(f"Time left: {mins}m {secs}s  (Completed {self._completed_count}/{len(self._states)})")

    # modifies: self
    # effects: adds text to the log
    def append_log(self, text: str):
        self.log_output.appendPlainText(text)