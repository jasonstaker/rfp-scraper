# src/scraper/scrapers/counties/florida/__init__.py

from .broward import BrowardScraper
from .hillsborough import HillsboroughScraper
from .orange import OrangeScraper
from .palm_beach import PalmBeachScraper

SCRAPER_MAP = {
    "broward": BrowardScraper,
    "hillsborough": HillsboroughScraper,
    "orange": OrangeScraper,
    "palm beach": PalmBeachScraper,
}