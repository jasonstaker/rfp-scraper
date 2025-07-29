# src/scraper/scrapers/counties/texas/__init__.py

from .bexar import BexarScraper
from .collin import CollinScraper
from .dallas import DallasScraper
from .denton import DentonScraper
from .harris import HarrisScraper

SCRAPER_MAP = {
    "bexar": BexarScraper,
    "collin": CollinScraper,
    "dallas": DallasScraper,
    "denton": DentonScraper,
    "harris": HarrisScraper,
}