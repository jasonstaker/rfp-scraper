# src/scraper/scrapers/counties/texas/__init__.py

from .bexar import BexarScraper
from .collin import CollinScraper
from .dallas import DallasScraper
from .denton import DentonScraper
from .harris import HarrisScraper
from .tarrant import TarrantScraper
from .travis import TravisScraper

SCRAPER_MAP = {
    "bexar": BexarScraper,
    "collin": CollinScraper,
    "dallas": DallasScraper,
    "denton": DentonScraper,
    "harris": HarrisScraper,
    "tarrant": TarrantScraper,
    "travis": TravisScraper,
}