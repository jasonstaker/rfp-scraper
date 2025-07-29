# src/scraper/scrapers/counties/pennsylvania/__init__.py

from .allegheny import AlleghenyScraper

SCRAPER_MAP = {
    "allegheny": AlleghenyScraper,
}