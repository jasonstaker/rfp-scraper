# scraper/scrapers/__init__.py
from .alabama import AlabamaScraper
from .arkansas import ArkansasScraper
from .arizona import ArizonaScraper
from .california import CaliforniaScraper
from .colorado import ColoradoScraper
from .connecticut import ConnecticutScraper
from .dc import DCScraper
from .delaware import DelawareScraper
from .florida import FloridaScraper
from .georgia import GeorgiaScraper
from .hawaii import HawaiiScraper
from .iowa import IowaScraper

SCRAPER_MAP = {
    "alabama": AlabamaScraper,
    "arkansas": ArkansasScraper,
    "arizona": ArizonaScraper,
    "california": CaliforniaScraper,
    "colorado": ColoradoScraper,
    "connecticut": ConnecticutScraper,
    "district of columbia": DCScraper,
    "delaware": DelawareScraper,
    "florida": FloridaScraper,
    "georgia": GeorgiaScraper,
    "hawaii": HawaiiScraper,
    "iowa": IowaScraper
}