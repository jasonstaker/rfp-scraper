# src/scraper/scrapers/counties/california/__init__.py

from .alameda import AlamedaScraper
from .contra_costa import ContraCostaScraper

SCRAPER_MAP = {
    "alameda": AlamedaScraper,
    "contra costa": ContraCostaScraper
}
