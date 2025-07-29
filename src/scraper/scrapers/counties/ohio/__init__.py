# src/scraper/scrapers/counties/ohio/__init__.py

from .cuyahoga import CuyahogaScraper
from .franklin import FranklinScraper

SCRAPER_MAP = {
    "cuyahoga": CuyahogaScraper,
    "franklin": FranklinScraper,
}