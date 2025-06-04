# text_utils.py

# requires: text is a string or none
# modifies: nothing
# effects: removes extra whitespace from text and returns the cleaned string; returns an empty string if text is none or empty
def clean_text(text):
    return " ".join(text.split()).strip() if text else ""