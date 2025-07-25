# src/scraper/scrapers/counties/california/__init__.py

from .alameda import AlamedaScraper
from .contra_costa import ContraCostaScraper
from .los_angeles import LosAngelesScraper
from .orange import OrangeScraper

SCRAPER_MAP = {
    "alameda": AlamedaScraper,
    "contra costa": ContraCostaScraper,
    "los angeles": LosAngelesScraper,
    "orange": OrangeScraper,
}
