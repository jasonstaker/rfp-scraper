# src/scraper/scrapers/counties/florida/__init__.py

from .broward import BrowardScraper
SCRAPER_MAP = {
    "broward": BrowardScraper,
}