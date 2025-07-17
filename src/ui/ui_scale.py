# ui_scale.py
from PyQt5.QtWidgets import QApplication

_BASE_WIDTH  = 2880
_BASE_HEIGHT = 1080

# requires: primaryScreen exists 
# effects: computes a uniform scale factor between the designed baseline and the user's screen
def compute_scale():
    screen = QApplication.primaryScreen()
    geo   = screen.availableGeometry()
    sx = geo.width()  / _BASE_WIDTH
    sy = geo.height() / _BASE_HEIGHT
    return min(sx, sy)

SCALE = compute_scale()

# effects: scales an integer pixel according to current screen
def px(value: int) -> int:
    return max(1, int(value * SCALE))