# src/scraper/scrapers/counties/utah/__init__.py

from .salt_lake import SaltLakeScraper

SCRAPER_MAP = {
    "salt lake": SaltLakeScraper,
}