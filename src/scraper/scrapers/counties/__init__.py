# src/scraper/scrapers/counties/__init__.py

from .arizona import SCRAPER_MAP as ARIZONA_COUNTIES
from .california import SCRAPER_MAP as CALIFORNIA_COUNTIES

SCRAPER_MAP = {
    "arizona": ARIZONA_COUNTIES,
    "california": CALIFORNIA_COUNTIES,
}
