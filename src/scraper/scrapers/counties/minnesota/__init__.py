# src/scraper/scrapers/counties/minnesota/__init__.py

from .hennepin import HennepinScraper

SCRAPER_MAP = {
    "hennepin": HennepinScraper,
}