"""Local QR Code and Barcode detector using pyzbar (0 tokens)."""

import io
from typing import NamedTuple, Optional
from PIL import Image
from core.logger import logger

# Lazy load pyzbar to avoid system shared library crash if libzbar0 is missing
try:
    from pyzbar.pyzbar import decode as _pyzbar_decode
except (ImportError, Exception):
    _pyzbar_decode = None


class QRScanResult(NamedTuple):
    """Result container for QR code scanning."""

    has_qr: bool
    payloads: list[str]


class QRDetector:
    """Detects and decodes QR codes and Barcodes from in-memory image bytes."""

    _unavailable_warned = False

    @classmethod
    def _warn_unavailable(cls) -> None:
        """Log a prominent one-time warning when pyzbar is missing."""
        if not cls._unavailable_warned:
            logger.warning(
                "QR SCANNER IS INACTIVE: libzbar0/pyzbar not available. "
                "QR-based phishing links in media pass undetected."
            )
            cls._unavailable_warned = True

    @classmethod
    def scan_image(cls, image_bytes: bytes) -> QRScanResult:
        """Scan image bytes and extract decoded QR contents."""
        if not image_bytes:
            return QRScanResult(has_qr=False, payloads=[])
        if _pyzbar_decode is None:
            cls._warn_unavailable()
            return QRScanResult(has_qr=False, payloads=[])

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert to grayscale for robust barcode/QR reading
                gray_img = img.convert("L")
                decoded_objects = _pyzbar_decode(gray_img)

                if not decoded_objects:
                    return QRScanResult(has_qr=False, payloads=[])

                payloads: list[str] = []
                for obj in decoded_objects:
                    try:
                        data_str = obj.data.decode("utf-8", errors="ignore").strip()
                        if data_str and data_str not in payloads:
                            payloads.append(data_str)
                    except Exception as decode_err:
                        logger.warning(f"Error decoding QR data chunk: {decode_err}")

                return QRScanResult(
                    has_qr=bool(payloads),
                    payloads=payloads,
                )

        except Exception as err:
            logger.warning(f"QR detection processing error: {err}")
            return QRScanResult(has_qr=False, payloads=[])
