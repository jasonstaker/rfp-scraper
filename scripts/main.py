import sys
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.config import ASSETS_DIR
from src.ui.ui_scale import px, compute_scale, SCALE
from pathlib import Path
from string import Template

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
    app = QApplication(sys.argv)

    from src.ui import ui_scale
    ui_scale.SCALE = ui_scale.compute_scale()

    from src.ui.ui_scale import px

    qss = load_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
