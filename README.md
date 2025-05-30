# RFP Scraper

**Modular, scalable Python RFP Scraper** for 50+ U.S. state procurement portals—plug-and-play scraper classes with Excel export.
*Tags:* `rfp` `procurement` `scraper` `selenium` `requests` `excel`

---

## 🔍 Why?

Manually monitoring 20+ keywords across 50+ state procurement websites is a huge time sink.
**RFP Scraper** centralizes all RFP postings into a single `.xlsx` file—so you never miss a bid.


## 🚀 Features

* 🔌 Modular core with base classes for `requests`- and `Selenium`-powered scrapers
* ✅ Out-of-the-box support for:

  * Arizona
  * California
  * (More Coming)
* 🗂️ Keyword list (`keywords.txt`): one keyword per line
* ⚙️ Simple settings link-up for new scrapers
* 📊 Excel export (`.xlsx`) plus basic logging (`scraper.log`)
* 📈 Scales easily to all 50 states by dropping in new scraper files

## 📂 Repo Layout
.  
├── output/  
│   ├── rfp_scraping_output.xlsx  
│   └── scraper.log  
├── scraper/  
│   ├── config/  
│   │   ├── keywords.txt  
│   │   └── settings.py  
│   ├── core/  
│   │   ├── base_scraper.py  
│   │   ├── requests_scraper.py  
│   │   └── selenium_scraper.py  
│   ├── exporters/  
│   │   └── excel_exporter.py  
│   ├── scrapers/  
│   │   ├── arizona.py  
│   │   └── california.py  
│   ├── tests/  
│   │   ├── test_core.py  
│   │   └── test_scrapers.py  
│   ├── utils/  
│   │   ├── data_utils.py  
│   │   ├── date_utils.py  
│   │   └── text_utils.py  
│   └── logging_config.py  
├── temp/  
├── venv/  
├── LICENSE  
├── main.py  
├── README.md  
└── requirements.txt  


## ⚙️ Installation

```bash
git clone https://github.com/jasonstaker/rfp-scraper.git
cd rfp-scraper
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Requires Python 3.x (tested on 3.13.3)


## 📖 Usage

```bash
# Run for all supported states:
python main.py --states all

# Or target specific states (space-separated lowercase names):
python main.py --states arizona california
```

* `--states all` runs every scraper in `scraper/scrapers/`
* `--states <name…>` for individual or multiple states
* Outputs:

  * `output/rfp_scraping_output.xlsx`
  * `output/scraper.log`

## 🛠️ Configuration

* `scraper/config/keywords.txt`
  Add one keyword per line. These are matched to identify relevant RFPs.
* `scraper/config/settings.py`
  Add the main URL or page config for your new scraper.
* Defaults are already sensible for most sites—tune only if needed.

## ➕ Adding a New State

1. Create a file in `scraper/scrapers/`, e.g., `illinois.py`
2. Subclass one of the base scrapers in `scraper/core/`:

   * `BaseScraper` for requests-based
   * `SeleniumScraper` for dynamic websites
3. Add its config to `settings.py`
4. Run it with:

   ```bash
   python main.py --states illinois
   ```

## ✅ Testing

Current tests cover:

* All core scraper base classes
* All utility functions (`data_utils`, `date_utils`, `text_utils`)

## 📦 Output Columns

The exported `.xlsx` file includes:

* Proposal Title
* State
* Solicitation #
* RFx Type
* Due Date
* Decision Date
* Keyword Hits

## 🤝 Contributing

This project is not accepting external contributions at this time.
If you have any ideas of how to contribute, please contact me through my information on my GitHub profile.

## 📄 License

Licensed under the MIT License. See `LICENSE` for full text.

## 📸 Screenshots
Sample Output for California with "System" as a keyword:
![Sample Excel Output](/assets/output_example.png)  