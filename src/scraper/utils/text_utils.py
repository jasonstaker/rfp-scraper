# text_utils.py

import html
import re

# effects: removes extra whitespace from text and returns the cleaned string
def normalize_whitespace(text):
    return " ".join(text.split()).strip() if text else ""

# effects: gets rid of characters that excel files cannot process
def sanitize(val):
    if not isinstance(val, str):
        return val

    if not hasattr(sanitize, "_CONTROL_RE"):
        sanitize._CONTROL_RE = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')
        sanitize._BOM_RE = re.compile(r'^\ufeff')

    s = html.unescape(val)
    s = sanitize._BOM_RE.sub("", s)
    s = sanitize._CONTROL_RE.sub("", s)
    return s