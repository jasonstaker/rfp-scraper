# src/scraper/scrapers/counties/florida/__init__.py

from .broward import BrowardScraper
from .hillsborough import HillsboroughScraper

SCRAPER_MAP = {
    "broward": BrowardScraper,
    "hillsborough": HillsboroughScraper,
}