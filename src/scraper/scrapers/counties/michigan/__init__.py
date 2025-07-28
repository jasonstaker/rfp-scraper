# src/scraper/scrapers/counties/michigan/__init__.py

from .oakland import OaklandScraper

SCRAPER_MAP = {
    "oakland": OaklandScraper,
}