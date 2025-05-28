# RFP Scraper
A modular framework for scraping state procurement websites.

## Setup
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux)
3. Install dependencies: `pip install -r requirements.txt`
4. Run the scraper: `python main.py arizona`

## Adding a New Scraper
1. Create a new file in `scrapers/` (e.g., `california.py`).
2. Define a class inheriting from `RequestsScraper` or `SeleniumScraper`.
3. Implement `search`, `next_page`, and `extract_data`.
4. Update `SCRAPER_MAP` in `scrapers/__init__.py`.