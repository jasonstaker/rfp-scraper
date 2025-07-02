# home_page.py

from PyQt5.QtCore import Qt, pyqtSignal, QRect, QSize, QTimer, QPoint
from PyQt5.QtGui import QColor, QPainter, QFont, QTextCharFormat, QTextFormat
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
)

from scraper.config.settings import AVAILABLE_STATES
from src.config import ASSETS_DIR, KEYWORDS_FILE

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
        font = QFont("Courier", 10)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    # requires: none
    # modifies: none
    # effects: computes line number area width
    def line_number_area_width(self) -> int:
        digits = 1
        max_blocks = max(1, self.blockCount())
        while max_blocks >= 10:
            max_blocks //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
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
                painter.drawText(0, top, self.line_number_area.width() - 5, font_metrics.height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


# page for keyword and state input
class HomePage(QWidget):
    start_run = pyqtSignal(str, list)

    # requires: none
    # modifies: self.code_editor, self.state_list, self.select_all_btn
    # effects: initializes ui for keyword and state selection
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        self.header_bar = QWidget()
        self.header_bar.setObjectName("header_bar")
        self.header_bar.setStyleSheet("background-color: #1A429A;")
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(12, 4, 12, 4)
        header_layout.setSpacing(0)
        self.kw_label = QLabel("Enter keywords (one per line):")
        self.kw_label.setStyleSheet("color: white;")
        header_layout.addWidget(self.kw_label, 2, alignment=Qt.AlignVCenter)
        self.state_label = QLabel("Select:")
        self.state_label.setObjectName("state_label")
        self.state_label.setStyleSheet("color: white;")
        header_layout.addWidget(self.state_label, 1, alignment=Qt.AlignVCenter)
        main_layout.addWidget(self.header_bar)
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(12, 0, 12, 12)
        row_layout.setSpacing(12)
        main_layout.addLayout(row_layout)
        self.code_editor = CodeEditor()
        self.code_editor.setObjectName("code_editor")
        self.code_editor.setPlaceholderText("e.g.\ngrant management\ncase management\nhome energy\n...")
        self.code_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        row_layout.addWidget(self.code_editor, 2)
        try:
            if KEYWORDS_FILE.exists():
                with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
                    contents = f.read()
                self.code_editor.setPlainText(contents)
        except Exception:
            pass
        center_container = QWidget()
        center_container.setObjectName("center_container")
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        center_container.setLayout(center_layout)
        self.state_list = QListWidget()
        self.state_list.setObjectName("state_list")
        for state in AVAILABLE_STATES:
            parts = state.split()
            if len(parts) == 2:
                # two-word states: capitalize both
                label = " ".join(p.capitalize() for p in parts)
            elif len(parts) == 3:
                # three-word states: only first and third
                label = f"{parts[0].capitalize()} {parts[1].lower()} {parts[2].capitalize()}"
            else:
                # single-word or others
                label = state.capitalize()

            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.state_list.addItem(item)
        self.state_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        center_layout.addWidget(self.state_list)
        self.select_all_btn = QPushButton("Select all")
        self.select_all_btn.setObjectName("select_all_btn")
        center_layout.addWidget(self.select_all_btn)
        self.select_all_btn.clicked.connect(self.on_select_all_toggled)
        self.state_list.itemChanged.connect(self._on_state_item_changed)
        row_layout.addWidget(center_container, 1)
        right_container = QWidget()
        right_container.setObjectName("right_container")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_container.setLayout(right_layout)
        right_layout.addStretch()
        self.run_button = QPushButton("Run")
        self.run_button.setObjectName("run_button")
        self.run_button.setMinimumWidth(100)
        right_layout.addWidget(self.run_button, alignment=Qt.AlignHCenter)
        right_layout.addStretch()
        row_layout.addWidget(right_container)
        self.run_button.clicked.connect(self.on_run_clicked)
        QTimer.singleShot(0, self._align_select_states_label)

    # requires: none
    # modifies: self.state_list, self.select_all_btn
    # effects: toggles all state selections
    def on_select_all_toggled(self):
        any_unchecked = any(self.state_list.item(i).checkState() == Qt.Unchecked for i in range(self.state_list.count()))
        new_state = Qt.Checked if any_unchecked else Qt.Unchecked
        for i in range(self.state_list.count()):
            self.state_list.item(i).setCheckState(new_state)
        self.select_all_btn.setText("Unselect all" if new_state == Qt.Checked else "Select all")

    # requires: none
    # modifies: start_run signal
    # effects: emits keywords and states for scraping
    def on_run_clicked(self):
        full_text = self.code_editor.toPlainText()
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        keywords = "\n".join(lines)
        selected = [self.state_list.item(i).text().lower() for i in range(self.state_list.count()) if self.state_list.item(i).checkState() == Qt.Checked]
        self.start_run.emit(keywords, selected)

    # requires: none
    # modifies: self.code_editor, self.state_list, self.select_all_btn
    # effects: clears input fields
    def reset_fields(self):
        self.code_editor.clear()
        for i in range(self.state_list.count()):
            self.state_list.item(i).setCheckState(Qt.Unchecked)
        self.select_all_btn.setText("Select all")

    # requires: item is a QListWidgetItem
    # modifies: item
    # effects: updates item appearance based on check state
    def _on_state_item_changed(self, item: QListWidgetItem):
        if item.checkState() == Qt.Checked:
            item.setBackground(QColor("#FFD486"))
            item.setForeground(QColor("#1A429A"))
        else:
            item.setBackground(QColor("#FFFFFF"))
            item.setForeground(QColor("#1A429A"))

    # requires: event is a QResizeEvent
    # modifies: self.state_label
    # effects: adjusts state label position
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._align_select_states_label()

    # requires: none
    # modifies: self.state_label
    # effects: aligns state label with list
    def _align_select_states_label(self):
        global_list_top_left = self.state_list.mapToGlobal(QPoint(0, 0))
        header_local = self.header_bar.mapFromGlobal(global_list_top_left)
        new_x = header_local.x()
        current_y = self.state_label.y()
        self.state_label.move(new_x, current_y)