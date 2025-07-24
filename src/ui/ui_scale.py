# ui_scale.py

from PyQt5.QtWidgets import QApplication

_BASE_WIDTH  = 2880
_BASE_HEIGHT = 1080

# requires: primaryScreen exists 
# effects: computes a uniform scale factor between the designed baseline and the user's screen
def compute_scale():
    app = QApplication.instance()
    if not app:
        return 1.0
    screen = app.primaryScreen()
    if not screen:
        return 1.0
    geo = screen.availableGeometry()
    sx = geo.width()  / _BASE_WIDTH
    sy = geo.height() / _BASE_HEIGHT
    return min(sx, sy)

SCALE = 1.0

# effects: scales an integer pixel according to current screen
def px(value: int) -> int:
    return max(1, int(value * SCALE))