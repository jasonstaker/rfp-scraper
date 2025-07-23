# text_utils.py

import re

# effects: removes extra whitespace from text and returns the cleaned string
def normalize_whitespace(text):
    return " ".join(text.split()).strip() if text else ""

# effects: gets rid of characters that excel files cannot process
def sanitize(val):
    if isinstance(val, str):
        val = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', val)
        val = val.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return val