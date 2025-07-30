# src/scraper/scrapers/counties/florida/__init__.py

from .broward import BrowardScraper
from .hillsborough import HillsboroughScraper
from .miami_dade import MiamiDadeScraper
from .orange import OrangeScraper
from .palm_beach import PalmBeachScraper

SCRAPER_MAP = {
    "broward": BrowardScraper,
    "hillsborough": HillsboroughScraper,
    "miami dade": MiamiDadeScraper,
    "orange": OrangeScraper,
    "palm beach": PalmBeachScraper,
}