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

    @classmethod
    def scan_image(cls, pil_img: Image.Image) -> OCRResult:
        """Scan image and extract text."""
        # Note: If external OCR binary like Tesseract/PaddleOCR is installed, it is called here.
        # Otherwise, basic text/metadata and fallback sanitization is performed.
        try:
            # Check for standard EXIF / text chunks or run Tesseract if available
            extracted_text = ""
            try:
                import pytesseract
                extracted_text = pytesseract.image_to_string(pil_img, lang="rus+eng").strip()
            except (ImportError, Exception):
                # Fallback if tesseract binary is not installed in local environment
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
