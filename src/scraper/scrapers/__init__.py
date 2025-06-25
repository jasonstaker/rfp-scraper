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
from .idaho import IdahoScraper
from .illinois import IllinoisScraper
from .indiana import IndianaScraper
from .kansas import KansasScraper
from .kentucky import KentuckyScraper
from .louisiana import LouisianaScraper
from .massachusetts import MassachusettsScraper
from .maryland import MarylandScraper
from .maine import MaineScraper
from .michigan import MichiganScraper
from .minnesota import MinnesotaScraper
from .missouri import MissouriScraper
from .mississippi import MississippiScraper
from .montana import MontanaScraper
from .north_carolina import NorthCarolinaScraper
from .north_dakota import NorthDakotaScraper
from .nebraska import NebraskaScraper
from .new_hampshire import NewHampshireScraper
from .new_jersey import NewJerseyScraper

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
    "iowa": IowaScraper,
    "idaho": IdahoScraper,
    "illinois": IllinoisScraper,
    "indiana": IndianaScraper,
    "kansas": KansasScraper,
    "kentucky": KentuckyScraper,
    "louisiana": LouisianaScraper,
    "massachusetts": MassachusettsScraper,
    "maryland": MarylandScraper,
    "maine": MaineScraper,
    "michigan": MichiganScraper,
    "minnesota": MinnesotaScraper,
    "missouri": MissouriScraper,
    "mississippi": MississippiScraper,
    "montana": MontanaScraper,
    "north carolina": NorthCarolinaScraper,
    "north dakota": NorthDakotaScraper,
    "nebraska": NebraskaScraper,
    "new hampshire": NewHampshireScraper,
    "new jersey": NewJerseyScraper
}