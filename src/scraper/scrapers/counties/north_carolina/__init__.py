# src/scraper/scrapers/counties/north_carolina/__init__.py

from .mecklenburg import MecklenburgScraper
from .wake import WakeScraper

SCRAPER_MAP = {
    "mecklenburg": MecklenburgScraper,
    "wake": WakeScraper,
}