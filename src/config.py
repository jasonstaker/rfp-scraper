# config.py

from pathlib import Path

# project root
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# resource directories
ASSETS_DIR      = PROJECT_ROOT / "assets"
OUTPUT_DIR      = Path.home() / "Desktop"
CACHE_DIR       = PROJECT_ROOT / "output" / "cache"
LOG_FILE        = PROJECT_ROOT / "output" / "scraper.log"
PERSISTENCE_DIR = PROJECT_ROOT / "persistence"
HIDDEN_IDS_FILE = PERSISTENCE_DIR / "hidden_ids.json"

# scraper config folder
SCRAPER_CONFIG_DIR = PROJECT_ROOT / "src" / "scraper" / "config"
KEYWORDS_FILE      = SCRAPER_CONFIG_DIR / "keywords.txt"

# defaults
DEFAULT_TIMEOUT   = 30
USER_AGENT        = "RFP-Scraper/1.0"
SELENIUM_HEADLESS = False
MAX_RETRIES       = 3

def ensure_dirs_exist():
    # create any needed directories if they don't already exist.
    for d in (ASSETS_DIR, OUTPUT_DIR, CACHE_DIR, PERSISTENCE_DIR):
        d.mkdir(parents=True, exist_ok=True)

def load_keywords() -> list[str]:
    # read one keyword per line from keywords.txt.
    if not KEYWORDS_FILE.exists():
        raise FileNotFoundError(f"Missing keywords.txt at {KEYWORDS_FILE}")
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
