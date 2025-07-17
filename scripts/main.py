import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from src.ui.main_window import MainWindow
from pathlib import Path
from src.config import ASSETS_DIR
from string import Template

# DPI scaling baseline
_BASE_WIDTH  = 2880
_BASE_HEIGHT = 1080

def compute_scale():
    screen = QApplication.primaryScreen()
    geo   = screen.availableGeometry()
    sx = geo.width()  / _BASE_WIDTH
    sy = geo.height() / _BASE_HEIGHT
    return min(sx, sy)

def px(value: int) -> int:
    return max(1, int(value * SCALE))

def load_stylesheet():
    qss_path = Path(ASSETS_DIR) / "styles.qss.tpl"
    if not qss_path.exists():
        return ""

    with open(qss_path, "r", encoding="utf-8") as f:
        raw_tpl = f.read()

    tpl = Template(raw_tpl)
    return tpl.substitute({
        "font_size_base":         f"{px(25)}px",
        "font_size_button":       f"{px(22)}px",
        "font_size_header":       f"{px(32)}px",
        "font_size_subheader":    f"{px(28)}px",
        "font_size_error":        f"{px(24)}px",
        "font_size_cell":         f"{px(22)}px",
        "font_size_table_head":   f"{px(22)}px",
        "padding_button_v":       f"{px(10)}px",
        "padding_button_h":       f"{px(20)}px",
        "min_button_height":      f"{px(50)}px",
        "padding_header":         f"{px(12)}px",
        "padding_code":           f"{px(10)}px",
        "padding_cell":           f"{px(14)}px",
        "padding_table":          f"{px(12)}px",
        "border_radius":          f"{px(8)}px",
        "border_radius_scroll":   f"{px(9)}px",
        "scrollbar_width":        f"{px(18)}px",
        "scrollbar_minlen":       f"{px(40)}px",
        "outline_width":          f"{px(4)}px",
        "outline_offset":         f"{px(2)}px",
    })

def main():
    global SCALE
    app = QApplication(sys.argv)
    SCALE = compute_scale()

    qss = load_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
