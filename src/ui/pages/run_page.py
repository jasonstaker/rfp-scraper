# run_page.py

import os
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

# page for showing scraper progress
class RunPage(QWidget):
    cancel_run = pyqtSignal()
    scraper_started = pyqtSignal()

    # requires: none
    # modifies: self._timer, self.log_output, self.cancel_button
    # effects: initializes ui for log display
    def __init__(self):
        super().__init__()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll_log_file)
        self._log_file_pos = 0
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        from src.ui.ui_scale import px
        main_layout.setContentsMargins(px(12), px(12), px(12), px(12))
        main_layout.setSpacing(px(8))
        info_label = QLabel("Scraper is running…")
        info_label.setObjectName("run_info_label")
        info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(info_label)
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

    # requires: none
    # modifies: self._log_file_pos, self.log_output, self._timer
    # effects: begins log file polling
    def start_tailing(self):
        self.scraper_started.emit()
        self._log_file_pos = os.path.getsize(LOG_FILE)
        self.log_output.clear()
        self._timer.start()

    # requires: none
    # modifies: self._timer
    # effects: stops log file polling
    def stop_tailing(self):
        if self._timer.isActive():
            self._timer.stop()

    # requires: none
    # modifies: self.log_output, self._log_file_pos
    # effects: appends new log lines
    def _poll_log_file(self):
        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._log_file_pos)
                new_data = f.read()
                if new_data:
                    lines = new_data.splitlines()
                    for line in lines:
                        self.log_output.appendPlainText(line)
                    self._log_file_pos = f.tell()
        except Exception as e:
            self.log_output.appendPlainText(f"<error reading log file: {e}>")
            self.stop_tailing()

    # requires: text is a string
    # modifies: self.log_output
    # effects: adds text to log display
    def append_log(self, text: str):
        self.log_output.appendPlainText(text)

    # requires: keywords is a string, states is a list of strings
    # modifies: none
    # effects: does nothing (placeholder)
    def start_scraper(self, keywords: str, states: list):
        pass