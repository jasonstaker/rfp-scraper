# scraper/scrapers/__init__.py
from .alabama import AlabamaScraper
from .arkansas import ArkansasScraper
from .arizona import ArizonaScraper
from .california import CaliforniaScraper
from .colorado import ColoradoScraper

SCRAPER_MAP = {
    "alabama": AlabamaScraper,
    "arkansas": ArkansasScraper,
    "arizona": ArizonaScraper,
    "california": CaliforniaScraper,
    "colorado": ColoradoScraper
}