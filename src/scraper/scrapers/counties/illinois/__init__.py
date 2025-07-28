# src/scraper/scrapers/counties/illinois/__init__.py

from .cook import CookScraper

SCRAPER_MAP = {
    "cook": CookScraper,
}