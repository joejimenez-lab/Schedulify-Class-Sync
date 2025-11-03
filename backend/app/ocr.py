import io
import os
from typing import List
import numpy as np
import cv2
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

def _preprocess_image(img_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    thr = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 9
    )
    return thr

def _img_to_text(img_bgr: np.ndarray) -> str:
    proc = _preprocess_image(img_bgr)
    config = "--psm 6"  # assume blocks of text
    return pytesseract.image_to_string(proc, config=config)

def _bytes_is_pdf(data: bytes) -> bool:
    return data[:4] == b"%PDF"

def ocr_to_text(data: bytes, max_pages: int = 3) -> str:
    """
    Returns OCR text from image bytes or PDF (first few pages).
    Requires poppler for pdf2image on some platforms.
    """
    texts: List[str] = []
    if _bytes_is_pdf(data):
        try:
            images: List[Image.Image] = convert_from_bytes(data, fmt="png", first_page=1, last_page=max_pages)
            for pil_im in images:
                arr = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
                texts.append(_img_to_text(arr))
        except Exception as e:
            # Fall back: try reading as image
            arr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                texts.append(_img_to_text(img))
            else:
                raise e
    else:
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Unsupported image format or corrupt bytes.")
        texts.append(_img_to_text(img))

    return "\n".join(texts).strip()
