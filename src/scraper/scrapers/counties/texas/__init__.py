# src/scraper/scrapers/counties/texas/__init__.py

from .bexar import BexarScraper

SCRAPER_MAP = {
    "bexar": BexarScraper,
}