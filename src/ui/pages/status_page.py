# status_page.py

import pandas as pd
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
from src.config import AVAILABLE_STATE_ABBR

# page for displaying scrape outcomes
class StatusPage(QWidget):
    back_to_home = pyqtSignal()

    # requires: none
    # modifies: self.state_table, self.county_table, self.error_label
    # effects: initializes UI with separate state and county result tables
    def __init__(self):
        super().__init__()
        from src.ui.ui_scale import px
        self.px = px

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(px(12), px(12), px(12), px(12))
        main_layout.setSpacing(px(8))
        self.setLayout(main_layout)

        header_label = QLabel("State Scrape Results")
        header_label.setObjectName("status_header_label")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet(f"font-weight: bold; font-size: {px(24)}px;")
        main_layout.addWidget(header_label)

        self.error_label = QLabel("")
        self.error_label.setObjectName("status_error_label")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        main_layout.addWidget(self.error_label)

        # State results table
        self.state_table = QTableWidget(0, 2)
        self._configure_table(self.state_table, header="state")
        main_layout.addWidget(self.state_table)

        # County results
        county_label = QLabel("County Scrape Results")
        county_label.setObjectName("county_header_label")
        county_label.setAlignment(Qt.AlignCenter)
        county_label.setStyleSheet(f"font-weight: bold; font-size: {px(24)}px;")
        main_layout.addWidget(county_label)

        self.county_table = QTableWidget(0, 2)
        self._configure_table(self.county_table, header="county")
        main_layout.addWidget(self.county_table)

        button_container = QWidget()
        button_container.setObjectName("status_button_container")
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)
        button_layout.addStretch()
        self.back_button = QPushButton("Back to filters")
        self.back_button.setObjectName("back_button")
        self.back_button.setMinimumWidth(px(120))
        button_layout.addWidget(self.back_button)
        button_layout.addStretch()
        main_layout.addWidget(button_container)

        self.back_button.clicked.connect(self.back_to_home.emit)

    def _configure_table(self, table: QTableWidget, header: str):
        table.horizontalHeader().setHighlightSections(False)
        table.verticalHeader().setHighlightSections(False)
        table.setObjectName("status_table")
        table.setHorizontalHeaderLabels([header, "status"])
        table.setColumnWidth(0, self.px(300))
        table.horizontalHeader().setStretchLastSection(True)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # requires: state_results is a dict mapping state->DataFrame,
    #           county_results is a dict mapping state->dict[county->DataFrame]
    # modifies: result tables and error_label
    # effects: populates state_table and county_table based on results
    def display_results(self,
                        state_results: dict[str, pd.DataFrame],
                        county_results: dict[str, dict[str, pd.DataFrame]]):
        self.error_label.clear()
        self.error_label.setVisible(False)
        if "_error" in state_results:
            self.error_label.setText(f"error: {state_results['_error']}")
            self.error_label.setVisible(True)

        # clear both tables
        self.state_table.setRowCount(0)
        self.county_table.setRowCount(0)

        state_row = 0
        county_row = 0

        # populate state table
        for state, df in state_results.items():
            if state.startswith("_"):
                continue

            pretty = state.title().replace(" Of ", " of ")
            tbl, r = self.state_table, state_row
            state_row += 1

            tbl.insertRow(r)
            region_item = QTableWidgetItem(pretty)
            region_item.setFlags(region_item.flags() ^ Qt.ItemIsEditable)
            tbl.setItem(r, 0, region_item)

            # status text logic
            if hasattr(df, "columns") and "success" in df.columns:
                success = bool(df["success"].iat[0])
                data_cols = [c for c in df.columns if c != "success"]
                placeholder = (df.shape[0] == 1 and success and df[data_cols].isna().all(axis=None))
                if not success:
                    status_text = "❌ Failed"
                elif placeholder:
                    status_text = "🔶 0 Found"
                else:
                    status_text = f"✅ {len(df)} Found"
            else:
                status_text = "❌ Failed"

            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(status_item.flags() ^ Qt.ItemIsEditable)
            tbl.setItem(r, 1, status_item)

            region_item.setTextAlignment(Qt.AlignCenter)
            status_item.setTextAlignment(Qt.AlignCenter)

        # populate county table
        for state, counties in county_results.items():
            abbr = AVAILABLE_STATE_ABBR.get(state, "")
            for county, df in counties.items():
                pretty = county.title()
                if abbr:
                    pretty += f", {abbr}"
                tbl, r = self.county_table, county_row
                county_row += 1

                tbl.insertRow(r)
                region_item = QTableWidgetItem(pretty)
                region_item.setFlags(region_item.flags() ^ Qt.ItemIsEditable)
                tbl.setItem(r, 0, region_item)

                # status text logic
                if hasattr(df, "columns") and "success" in df.columns:
                    success = bool(df["success"].iat[0])
                    data_cols = [c for c in df.columns if c != "success"]
                    placeholder = (df.shape[0] == 1 and success and df[data_cols].isna().all(axis=None))
                    if not success:
                        status_text = "❌ Failed"
                    elif placeholder:
                        status_text = "🔶 0 Found"
                    else:
                        status_text = f"✅ {len(df)} Found"
                else:
                    status_text = "❌ Failed"

                status_item = QTableWidgetItem(status_text)
                status_item.setFlags(status_item.flags() ^ Qt.ItemIsEditable)
                tbl.setItem(r, 1, status_item)

                region_item.setTextAlignment(Qt.AlignCenter)
                status_item.setTextAlignment(Qt.AlignCenter)

        # placeholders if empty
        if state_row == 0:
            self.state_table.insertRow(0)
            place = QTableWidgetItem("No completed scrapes")
            place.setFlags(place.flags() ^ Qt.ItemIsEditable)
            self.state_table.setItem(0, 0, place)
            self.state_table.setItem(0, 1, QTableWidgetItem("-"))
            place.setTextAlignment(Qt.AlignCenter)
            self.state_table.item(0, 1).setTextAlignment(Qt.AlignCenter)

        if county_row == 0:
            self.county_table.insertRow(0)
            place = QTableWidgetItem("No completed scrapes")
            place.setFlags(place.flags() ^ Qt.ItemIsEditable)
            self.county_table.setItem(0, 0, place)
            self.county_table.setItem(0, 1, QTableWidgetItem("-"))
            place.setTextAlignment(Qt.AlignCenter)
            self.county_table.item(0, 1).setTextAlignment(Qt.AlignCenter)
