# src/scraper/scrapers/counties/california/__init__.py

from .alameda import AlamedaScraper
from .contra_costa import ContraCostaScraper
from .los_angeles import LosAngelesScraper
from .orange import OrangeScraper
from .sacramento import SacramentoScraper
from .san_bernadino import SanBernadinoScraper
from .santa_clara import SantaClaraScraper

SCRAPER_MAP = {
    "alameda": AlamedaScraper,
    "contra costa": ContraCostaScraper,
    "los angeles": LosAngelesScraper,
    "orange": OrangeScraper,
    "sacramento": SacramentoScraper,
    "san bernadino": SanBernadinoScraper,
    "santa clara": SantaClaraScraper
}
