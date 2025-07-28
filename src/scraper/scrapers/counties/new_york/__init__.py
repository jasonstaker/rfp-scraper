# src/scraper/scrapers/counties/new_york/__init__.py

from .every import EveryNYScraper

SCRAPER_MAP = {
    "every": EveryNYScraper,
}