# home_page.py

from PyQt5.QtCore import Qt, pyqtSignal, QRect, QSize, QTimer
from PyQt5.QtGui import QColor, QPainter, QFont, QTextCharFormat, QTextFormat
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
)

from persistence.average_time_manager import load_averages, estimate_total_time, update_averages
from src.config import AVAILABLE_STATES, AVAILABLE_COUNTIES_BY_STATE, KEYWORDS_FILE, AVAILABLE_STATE_ABBR


# line number display for code editor
class LineNumberArea(QWidget):

    # requires: editor is a CodeEditor instance
    # modifies: self.code_editor
    # effects: initializes line number area
    def __init__(self, editor: 'CodeEditor'):
        super().__init__(editor)
        self.code_editor = editor

    # requires: none
    # modifies: none
    # effects: returns size hint for line number area
    def sizeHint(self) -> QSize:
        return QSize(self.code_editor.line_number_area_width(), 0)

    # requires: event is a QPaintEvent
    # modifies: none
    # effects: renders line numbers
    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


# text editor with line numbering
class CodeEditor(QPlainTextEdit):
    # requires: parent is a QWidget or None
    # modifies: self.line_number_area
    # effects: initializes editor with line numbers
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        from src.ui.ui_scale import px
        font = QFont("Courier", px(10))
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    # requires: none
    # modifies: none
    # effects: computes line number area width
    def line_number_area_width(self) -> int:
        from src.ui.ui_scale import px
        digits = 1
        max_blocks = max(1, self.blockCount())
        while max_blocks >= 10:
            max_blocks //= 10
            digits += 1
        space = px(3) + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    # requires: none
    # modifies: viewport margins
    # effects: adjusts margin for line numbers
    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    # requires: rect is a QRect, dy is an integer
    # modifies: self.line_number_area
    # effects: updates line number area on scroll
    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    # requires: event is a QResizeEvent
    # modifies: self.line_number_area
    # effects: resizes line number area
    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    # requires: none
    # modifies: self extra selections
    # effects: highlights current line
    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(Qt.yellow).lighter(160)
            fmt = QTextCharFormat()
            fmt.setBackground(line_color)
            fmt.setProperty(QTextFormat.FullWidthSelection, True)
            selection.format = fmt
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    # requires: event is a QPaintEvent
    # modifies: none
    # effects: paints line numbers
    def line_number_area_paint_event(self, event):
        from src.ui.ui_scale import px
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#1A429A"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#FFFFFF"))
                font_metrics = self.fontMetrics()
                painter.drawText(0, top, self.line_number_area.width() - px(5), font_metrics.height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


# page for keyword, state, and county input
class HomePage(QWidget):
    start_run = pyqtSignal(str, list, dict)

    # requires: none
    # modifies: self.code_editor, self.tab_widget, self.select_buttons, self.counties
    # effects: initializes ui for keyword, state, and county selection with tabs
    def __init__(self):
        super().__init__()
        from src.ui.ui_scale import px
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(px(0), px(8), px(0), px(0))
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        # Header bar
        self.header_bar = QWidget()
        self.header_bar.setObjectName("header_bar")
        self.header_bar.setStyleSheet("background-color: #1A429A;")
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(px(12), px(4), px(12), px(4))
        header_layout.setSpacing(0)

        self.kw_label = QLabel("Enter keywords (one per line):")
        self.kw_label.setStyleSheet("color: white;")
        header_layout.addWidget(self.kw_label, 2, alignment=Qt.AlignVCenter)

        main_layout.addWidget(self.header_bar)

        # Content row
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(px(12), px(0), px(12), px(12))
        row_layout.setSpacing(px(12))
        main_layout.addLayout(row_layout)

        # Keyword editor
        self.code_editor = CodeEditor()
        self.code_editor.setObjectName("code_editor")
        self.code_editor.setPlaceholderText("e.g.\ngrant management\nLIHEAP\n...")
        self.code_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        row_layout.addWidget(self.code_editor, 2)

        try:
            with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
                existing = f.read().rstrip("\n")
                if existing:
                    self.code_editor.setPlainText(existing)
        except FileNotFoundError:
            pass

        # Tabs for States and Counties
        self.tab_widget = QTabWidget()
        # States tab
        state_page = QWidget()
        sp_layout = QVBoxLayout(state_page)
        sp_layout.setContentsMargins(0, 0, 0, 0)
        sp_layout.setSpacing(px(8))
        self.state_list = QListWidget()
        self.state_list.setObjectName("state_list")
        for state in AVAILABLE_STATES:
            item = QListWidgetItem(" ".join(p.capitalize() for p in state.split()))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, state)
            self.state_list.addItem(item)
        sp_layout.addWidget(self.state_list)
        self.state_select_all = QPushButton("Select all")
        self.state_select_all.setObjectName("select_all_btn")
        self.state_select_all.clicked.connect(lambda: self._toggle(self.state_list, self.state_select_all))
        sp_layout.addWidget(self.state_select_all)
        self.tab_widget.addTab(state_page, "States")

        # Counties tab
        county_page = QWidget()
        cp_layout = QVBoxLayout(county_page)
        cp_layout.setContentsMargins(0, 0, 0, 0)
        cp_layout.setSpacing(px(8))
        self.county_list = QListWidget()
        self.county_list.setObjectName("state_list")  # reuse same QSS ID
        for state, counties in AVAILABLE_COUNTIES_BY_STATE.items():
            for county in counties:
                abbr = AVAILABLE_STATE_ABBR[state]
                display = f"{county.title()} County, {abbr}"
                item = QListWidgetItem(display)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                item.setData(Qt.UserRole, (state, county))
                self.county_list.addItem(item)
        cp_layout.addWidget(self.county_list)
        self.county_select_all = QPushButton("Select all")
        self.county_select_all.setObjectName("select_all_btn")
        self.county_select_all.clicked.connect(lambda: self._toggle(self.county_list, self.county_select_all))
        cp_layout.addWidget(self.county_select_all)
        self.tab_widget.addTab(county_page, "Counties")

        row_layout.addWidget(self.tab_widget, 1)

        # Placeholder for county selections
        self.counties = {}

        # Time estimate & Run button
        right_container = QWidget()
        right_container.setObjectName("right_container")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(px(8))

        self.estimated_time_label = QLabel("Estimated time:")
        self.estimated_time_label.setAlignment(Qt.AlignHCenter)
        self.estimated_time_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(self.estimated_time_label)

        self.estimated_time_value = QLabel("~0 min")
        self.estimated_time_value.setAlignment(Qt.AlignHCenter)
        self.set_estimated_time(0, 0)
        right_layout.addWidget(self.estimated_time_value)

        right_layout.addStretch()
        self.run_button = QPushButton("Run")
        self.run_button.setObjectName("run_button")
        self.run_button.setMinimumWidth(px(100))
        right_layout.addWidget(self.run_button, alignment=Qt.AlignHCenter)
        right_layout.addStretch()
        row_layout.addWidget(right_container)

        # Connections
        self.run_button.clicked.connect(self.on_run_clicked)
        self.tab_widget.currentChanged.connect(self.recalc_estimated_time)
        self.state_list.itemChanged.connect(self.recalc_estimated_time)
        self.county_list.itemChanged.connect(self.recalc_estimated_time)
        QTimer.singleShot(0, self.recalc_estimated_time)

    # requires: list_widget and button
    # modifies: check states of items
    # effects: toggles all checkboxes and updates button text
    def _toggle(self, list_widget, button):
        any_unchecked = any(
            list_widget.item(i).checkState() == Qt.Unchecked
            for i in range(list_widget.count())
        )
        new_state = Qt.Checked if any_unchecked else Qt.Unchecked
        for i in range(list_widget.count()):
            list_widget.item(i).setCheckState(new_state)
        button.setText("Unselect all" if new_state == Qt.Checked else "Select all")

    # requires: none
    # modifies: self.estimated_time_value
    # effects: recalculates based on selected states & counties
    def recalc_estimated_time(self):
        averages = load_averages()
        states = [
            self.state_list.item(i).data(Qt.UserRole)
            for i in range(self.state_list.count())
            if self.state_list.item(i).checkState() == Qt.Checked
        ]
        counties: dict[str, list[str]] = {}
        for i in range(self.county_list.count()):
            if self.county_list.item(i).checkState() == Qt.Checked:
                st, co = self.county_list.item(i).data(Qt.UserRole)
                counties.setdefault(st, []).append(co)
        mins, secs = estimate_total_time(averages, states, counties)
        self.set_estimated_time(mins, secs)

    # requires: minutes, seconds
    # modifies: time label
    # effects: updates display
    def set_estimated_time(self, minutes: int, seconds: int):
        parts = []
        if minutes > 0:
            parts.append(f"{minutes} min")
        if seconds > 0 or not parts:
            parts.append(f"{seconds} sec")
        self.estimated_time_value.setText("~" + " ".join(parts))

    # requires: none
    # modifies: start_run signal
    # effects: emits keywords, states, and counties
    def on_run_clicked(self):
        keywords = self.code_editor.toPlainText().strip()
        states = [
            self.state_list.item(i).data(Qt.UserRole)
            for i in range(self.state_list.count())
            if self.state_list.item(i).checkState() == Qt.Checked
        ]
        counties_by_state: dict[str, list[str]] = {}
        for i in range(self.county_list.count()):
            if self.county_list.item(i).checkState() != Qt.Checked:
                continue
            st, co = self.county_list.item(i).data(Qt.UserRole)  # unpack our tuple
            counties_by_state.setdefault(st, []).append(co)

        self.start_run.emit(keywords, states, counties_by_state)

    # requires: none
    # modifies: fields
    # effects: resets editor, lists, and buttons
    def reset_fields(self):
        self.code_editor.clear()
        for lw in (self.state_list, self.county_list):
            for i in range(lw.count()):
                lw.item(i).setCheckState(Qt.Unchecked)
        self.state_select_all.setText("Select all")
        self.county_select_all.setText("Select all")

    # requires: timings
    # modifies: persistence
    # effects: updates averages
    def persist_averages(self, timings: dict[str, float]):
        update_averages(timings)
