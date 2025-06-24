# status_page.py
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QSizePolicy,
    QHBoxLayout,
)

# page for displaying scrape outcomes
class StatusPage(QWidget):
    back_to_home = pyqtSignal()

    # requires: none
    # modifies: self.table, self.error_label
    # effects: initializes ui with results table
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        header_label = QLabel("Scrape results")
        header_label.setObjectName("status_header_label")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("font-weight: bold; font-size: 24px;")
        main_layout.addWidget(header_label)
        self.error_label = QLabel("")
        self.error_label.setObjectName("status_error_label")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        main_layout.addWidget(self.error_label)
        self.table = QTableWidget(0, 2)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().setHighlightSections(False)
        self.table.setObjectName("status_table")
        self.table.setHorizontalHeaderLabels(["state", "status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.table)
        button_container = QWidget()
        button_container.setObjectName("status_button_container")
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)
        button_layout.addStretch()
        self.back_button = QPushButton("Back to filters")
        self.back_button.setObjectName("back_button")
        self.back_button.setMinimumWidth(120)
        button_layout.addWidget(self.back_button)
        button_layout.addStretch()
        main_layout.addWidget(button_container)
        self.back_button.clicked.connect(self.back_to_home.emit)

    # requires: results is a dictionary
    # modifies: self.table, self.error_label
    # effects: displays scraping results in table
    def display_results(self, results: dict):
        self.error_label.clear()
        self.error_label.setVisible(False)
        if "_error" in results:
            error_text = results["_error"]
            self.error_label.setText(f"error: {error_text}")
            self.error_label.setVisible(True)
        self.table.setRowCount(0)
        row_index = 0
        for key, payload in results.items():
            if key.startswith("_"):
                continue
            self.table.insertRow(row_index)
            state_item = QTableWidgetItem(key.capitalize())
            state_item.setFlags(state_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row_index, 0, state_item)
            if hasattr(payload, "columns") and "success" in payload.columns:
                success_flag = bool(payload["success"].iat[0])
            else:
                success_flag = bool(payload)
            status_text = "✅ Passed" if success_flag else "❌ Failed"
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(status_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row_index, 1, status_item)
            state_item.setTextAlignment(Qt.AlignCenter)
            status_item.setTextAlignment(Qt.AlignCenter)
            row_index += 1
        if row_index == 0:
            self.table.setRowCount(1)
            placeholder = QTableWidgetItem("No completed scrapes")
            placeholder.setFlags(placeholder.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(0, 0, placeholder)
            self.table.setItem(0, 1, QTableWidgetItem("-"))
            placeholder.setTextAlignment(Qt.AlignHCenter)
            self.table.item(0, 1).setTextAlignment(Qt.AlignCenter)