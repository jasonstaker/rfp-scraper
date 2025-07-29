# src/scraper/scrapers/counties/__init__.py

from .arizona import SCRAPER_MAP as ARIZONA_COUNTIES
from .california import SCRAPER_MAP as CALIFORNIA_COUNTIES
from .florida import SCRAPER_MAP as FLORIDA_COUNTIES
from .georgia import SCRAPER_MAP as GEORGIA_COUNTIES
from .illinois import SCRAPER_MAP as ILLINOIS_COUNTIES
from .massachusetts import SCRAPER_MAP as MASSACHUSETTS_COUNTIES
from .maryland import SCRAPER_MAP as MARYLAND_COUNTIES
from .michigan import SCRAPER_MAP as MICHIGAN_COUNTIES
from .minnesota import SCRAPER_MAP as MINNESOTA_COUNTIES
from .north_carolina import SCRAPER_MAP as NORTH_CAROLINA_COUNTIES
from .nevada import SCRAPER_MAP as NEVADA_COUNTIES
from .new_york import SCRAPER_MAP as NEW_YORK_COUNTIES
from .ohio import SCRAPER_MAP as OHIO_COUNTIES
from .pennsylvania import SCRAPER_MAP as PENNSYLVANIA_COUNTIES
from .texas import SCRAPER_MAP as TEXAS_COUNTIES

SCRAPER_MAP = {
    "arizona": ARIZONA_COUNTIES,
    "california": CALIFORNIA_COUNTIES,
    "florida": FLORIDA_COUNTIES,
    "georgia": GEORGIA_COUNTIES,
    "illinois": ILLINOIS_COUNTIES,
    "massachusetts": MASSACHUSETTS_COUNTIES,
    "maryland": MARYLAND_COUNTIES,
    "michigan": MICHIGAN_COUNTIES,
    "minnesota": MINNESOTA_COUNTIES,
    "north carolina": NORTH_CAROLINA_COUNTIES,
    "nevada": NEVADA_COUNTIES,
    "new york": NEW_YORK_COUNTIES,
    "ohio": OHIO_COUNTIES,
    "pennsylvania": PENNSYLVANIA_COUNTIES,
    "texas": TEXAS_COUNTIES,
}
