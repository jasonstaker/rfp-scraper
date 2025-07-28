# src/scraper/scrapers/counties/massachusetts/__init__.py

from .middlesex import MiddlesexScraper

SCRAPER_MAP = {
    "middlesex": MiddlesexScraper,
}