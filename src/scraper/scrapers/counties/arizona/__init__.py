# src/scraper/scrapers/counties/california/__init__.py

from .maricopa import MaricopaScraper

SCRAPER_MAP = {
    "maricopa": MaricopaScraper,
}
