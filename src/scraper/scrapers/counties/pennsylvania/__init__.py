# src/scraper/scrapers/counties/pennsylvania/__init__.py

from .allegheny import AlleghenyScraper
from .philadelphia import PhiladelphiaScraper

SCRAPER_MAP = {
    "allegheny": AlleghenyScraper,
    "philadelphia": PhiladelphiaScraper,
}