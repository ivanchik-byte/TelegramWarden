"""OCR text extraction module from screenshots and image banners."""

import io
from typing import NamedTuple, Optional
from PIL import Image
from core.logger import logger
from services.ai.normalizer import TextSanitizer, SanitizedTextResult


class OCRResult(NamedTuple):
    """Result container for OCR text extraction."""

    extracted_text: str
    sanitized: SanitizedTextResult
    has_text: bool


class OCREngine:
    """Extracts text from images and checks for embedded contact links and spam."""

    _unavailable_warned = False

    @classmethod
    def _warn_unavailable(cls) -> None:
        """Log a prominent one-time warning when tesseract is missing."""
        if not cls._unavailable_warned:
            logger.warning(
                "OCR SCANNER IS INACTIVE: pytesseract/tesseract binary not available. "
                "Spam text inside images passes undetected."
            )
            cls._unavailable_warned = True

    @classmethod
    def scan_image(cls, pil_img: Image.Image) -> OCRResult:
        """Scan image and extract text."""
        try:
            extracted_text = ""
            try:
                import pytesseract
                extracted_text = pytesseract.image_to_string(pil_img, lang="rus+eng").strip()
            except ImportError:
                cls._warn_unavailable()
                extracted_text = ""
            except Exception as ocr_err:
                # Tesseract present but failed on this frame: not an install problem
                logger.debug(f"Tesseract OCR error on frame: {ocr_err}")
                extracted_text = ""

            sanitized = TextSanitizer.sanitize(extracted_text)
            return OCRResult(
                extracted_text=extracted_text,
                sanitized=sanitized,
                has_text=bool(extracted_text),
            )
        except Exception as err:
            logger.debug(f"OCR scanning error: {err}")
            empty_sanitized = TextSanitizer.sanitize("")
            return OCRResult(extracted_text="", sanitized=empty_sanitized, has_text=False)
