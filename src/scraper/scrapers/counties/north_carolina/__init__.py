# src/scraper/scrapers/counties/north_carolina/__init__.py

from .mecklenburg import MecklenburgScraper

SCRAPER_MAP = {
    "mecklenburg": MecklenburgScraper,
}