# ocr.py
from __future__ import annotations
from typing import Optional
import io
try:
    from PIL import Image
    import pytesseract
except Exception:
    Image = None
    pytesseract = None

def extract_text(image_bytes: bytes) -> Optional[str]:
    """Return plain text from the screenshot using Tesseract."""
    if Image is None or pytesseract is None:
        return None
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)
