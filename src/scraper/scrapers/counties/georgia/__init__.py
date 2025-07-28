# src/scraper/scrapers/counties/georgia/__init__.py

from .fulton import FultonScraper
from .gwinnett import GwinnettScraper

SCRAPER_MAP = {
    "fulton": FultonScraper,
    "gwinnett": GwinnettScraper,
}