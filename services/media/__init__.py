"""Local Media Processing and Vision Engine package."""

from services.media.phash import PHashDeduplicator
from services.media.qr_detector import QRDetector, QRScanResult
from services.media.video_sampler import VideoKeyframeSampler
from services.media.nsfw_detector import NSFWDetector, NSFWDetectionResult, nsfw_detector
from services.media.ocr_engine import OCREngine, OCRResult
from services.media.pipeline import MediaModerationPipeline, MediaModerationVerdict

__all__ = [
    "PHashDeduplicator",
    "QRDetector",
    "QRScanResult",
    "VideoKeyframeSampler",
    "NSFWDetector",
    "NSFWDetectionResult",
    "nsfw_detector",
    "OCREngine",
    "OCRResult",
    "MediaModerationPipeline",
    "MediaModerationVerdict",
]
