# src/scraper/scrapers/counties/texas/__init__.py

from .bexar import BexarScraper
from .collin import CollinScraper
from .dallas import DallasScraper
from .denton import DentonScraper

SCRAPER_MAP = {
    "bexar": BexarScraper,
    "collin": CollinScraper,
    "dallas": DallasScraper,
    "denton": DentonScraper,
}