# src/scraper/scrapers/counties/ohio/__init__.py

from .cuyahoga import CuyahogaScraper

SCRAPER_MAP = {
    "cuyahoga": CuyahogaScraper,
}