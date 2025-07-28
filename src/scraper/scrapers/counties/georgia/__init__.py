# src/scraper/scrapers/counties/georgia/__init__.py

from .fulton import FultonScraper

SCRAPER_MAP = {
    "fulton": FultonScraper,
}