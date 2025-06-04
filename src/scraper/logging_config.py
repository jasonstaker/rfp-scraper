# logging_config.py
import logging
from logging import FileHandler
from logging import Formatter

# a custom logging formatter that adjusts logger names for better readability
class CustomFormatter(Formatter):
    # requires: nothing
    # modifies: record.name
    # effects: formats the log record by adjusting logger names and returns the formatted string
    def format(self, record):
        if record.name == 'root':
            record.name = '[main]'
        elif record.name.startswith('scraper.scrapers.') or record.name.startswith('scraper.exporters.'):
            file_name = record.name.split('.')[-1]
            record.name = f'[{file_name}]'
        return super().format(record)

# requires: log_file is a string or Path object specifying the log file path
# modifies: the logging configuration
# effects: sets up logging to write to log_file with a custom formatter and suppresses unwanted logs from specific libraries
def configure_logging(log_file):
    handler = FileHandler(log_file)
    formatter = CustomFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    # Set levels for specific loggers to suppress unwanted output
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('WDM').setLevel(logging.WARNING)