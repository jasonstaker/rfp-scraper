# src/scraper/scrapers/counties/california/__init__.py

from .alameda import AlamedaScraper

SCRAPER_MAP = {
    "alameda": AlamedaScraper,
}
