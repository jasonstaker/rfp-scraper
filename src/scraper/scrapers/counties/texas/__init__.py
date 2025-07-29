# src/scraper/scrapers/counties/texas/__init__.py

from .bexar import BexarScraper
from .collin import CollinScraper

SCRAPER_MAP = {
    "bexar": BexarScraper,
    "collin": CollinScraper,
}