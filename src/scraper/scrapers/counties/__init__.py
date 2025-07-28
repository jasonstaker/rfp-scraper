# src/scraper/scrapers/counties/__init__.py

from .arizona import SCRAPER_MAP as ARIZONA_COUNTIES
from .california import SCRAPER_MAP as CALIFORNIA_COUNTIES
from .florida import SCRAPER_MAP as FLORIDA_COUNTIES
from .georgia import SCRAPER_MAP as GEORGIA_COUNTIES
from .illinois import SCRAPER_MAP as ILLINOIS_COUNTIES

SCRAPER_MAP = {
    "arizona": ARIZONA_COUNTIES,
    "california": CALIFORNIA_COUNTIES,
    "florida": FLORIDA_COUNTIES,
    "georgia": GEORGIA_COUNTIES,
    "illinois": ILLINOIS_COUNTIES,
}
