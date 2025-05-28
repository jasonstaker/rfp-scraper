# scraper/scrapers/__init__.py
from .arizona import ArizonaScraper
from .california import CaliforniaScraper

SCRAPER_MAP = {
    "arizona": ArizonaScraper,
    "california": CaliforniaScraper
}