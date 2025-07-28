# src/scraper/scrapers/counties/maryland/__init__.py

from .montgomery import MontgomeryScraper

SCRAPER_MAP = {
    "montgomery": MontgomeryScraper,
}