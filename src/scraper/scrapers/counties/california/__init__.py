# src/scraper/scrapers/counties/california/__init__.py

from .alameda import AlamedaScraper
from .contra_costa import ContraCostaScraper
from .fresno import FresnoScraper
from .los_angeles import LosAngelesScraper
from .orange import OrangeScraper
from .riverside import RiversideScraper
from .sacramento import SacramentoScraper
from .san_bernadino import SanBernadinoScraper
from .santa_clara import SantaClaraScraper
from .san_diego import SanDiegoScraper

SCRAPER_MAP = {
    "alameda": AlamedaScraper,
    "contra costa": ContraCostaScraper,
    "fresno": FresnoScraper,
    "los angeles": LosAngelesScraper,
    "orange": OrangeScraper,
    "riverside": RiversideScraper,
    "sacramento": SacramentoScraper,
    "san bernadino": SanBernadinoScraper,
    "santa clara": SantaClaraScraper,
    "san diego": SanDiegoScraper,
}
