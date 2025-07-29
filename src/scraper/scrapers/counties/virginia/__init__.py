# src/scraper/scrapers/counties/virginia/__init__.py

from .fairfax import FairfaxScraper

SCRAPER_MAP = {
    "fairfax": FairfaxScraper,
}