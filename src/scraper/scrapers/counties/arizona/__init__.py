# src/scraper/scrapers/counties/arizona/__init__.py

from .maricopa import MaricopaScraper
from .pima import PimaScraper

SCRAPER_MAP = {
    "maricopa": MaricopaScraper,
    "pima": PimaScraper,
}
