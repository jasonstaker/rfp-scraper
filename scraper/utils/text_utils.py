# text_utils.py
def clean_text(text):
    return " ".join(text.split()).strip() if text else ""