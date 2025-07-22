# text_utils.py

import re

# requires: text is a string or none
# modifies: nothing
# effects: removes extra whitespace from text and returns the cleaned string; returns an empty string if text is none or empty
def clean_text(text):
    return " ".join(text.split()).strip() if text else ""

def sanitize(val):
    if isinstance(val, str):
        val = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', val)
        val = val.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return val