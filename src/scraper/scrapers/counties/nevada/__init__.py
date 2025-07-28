# src/scraper/scrapers/counties/nevada/__init__.py

from .clark import ClarkScraper

SCRAPER_MAP = {
    "clark": ClarkScraper,
}