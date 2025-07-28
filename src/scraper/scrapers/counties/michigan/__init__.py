# src/scraper/scrapers/counties/michigan/__init__.py

from .oakland import OaklandScraper
from .wayne import WayneScraper

SCRAPER_MAP = {
    "oakland": OaklandScraper,
    "wayne": WayneScraper,
}