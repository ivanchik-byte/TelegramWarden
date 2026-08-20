"""Unified Media Moderation Pipeline orchestrating QR, pHash, NSFW, and OCR."""

import io
from typing import NamedTuple, Optional
from PIL import Image
from core.logger import logger
from services.ai.schema import SuggestedAction, ViolationCategory
from services.media.nsfw_detector import nsfw_detector
from services.media.ocr_engine import OCREngine
from services.media.phash import PHashDeduplicator
from services.media.qr_detector import QRDetector
from services.media.video_sampler import VideoKeyframeSampler


class MediaModerationVerdict(NamedTuple):
    """Result of media file inspection."""

    is_violation: bool
    category: ViolationCategory
    confidence: float
    reason: str
    suggested_action: SuggestedAction
    evidence_frame_bytes: Optional[bytes]


class MediaModerationPipeline:
    """Orchestrates all media scanning steps with zero unnecessary token costs."""

    @classmethod
    async def process_media(
        cls,
        media_bytes: bytes,
        media_type: str = "photo",  # 'photo', 'video', 'video_note', 'sticker', 'animation'
    ) -> MediaModerationVerdict:
        """Process incoming image or video through local detection layers."""
        if not media_bytes:
            return MediaModerationVerdict(
                is_violation=False,
                category=ViolationCategory.CLEAN,
                confidence=0.0,
                reason="Empty media payload",
                suggested_action=SuggestedAction.PASS_MESSAGE,
                evidence_frame_bytes=None,
            )

        # 1. pHash Spam Check (1 ms)
        phash_str = PHashDeduplicator.compute_hash(media_bytes)
        if phash_str and await PHashDeduplicator.is_known_spam(phash_str):
            logger.info("Known spam pHash detected in media pipeline")
            return MediaModerationVerdict(
                is_violation=True,
                category=ViolationCategory.COMMERCIAL_AD,
                confidence=99.0,
                reason="Обнаружен известный спам по визуальному отпечатку (pHash)",
                suggested_action=SuggestedAction.BAN_USER,
                evidence_frame_bytes=media_bytes,
            )

        # 2. Frame Extraction
        frames: list[Image.Image] = []
        if media_type in ("video", "video_note"):
            frames = VideoKeyframeSampler.sample_keyframes(media_bytes, num_frames=5)
        else:
            try:
                with Image.open(io.BytesIO(media_bytes)) as pil_img:
                    frames = [pil_img.convert("RGB")]
            except Exception as err:
                logger.warning(f"Failed to open image bytes: {err}")
                frames = []

        if not frames:
            # Fallback if format is undecodable
            return MediaModerationVerdict(
                is_violation=False,
                category=ViolationCategory.CLEAN,
                confidence=0.0,
                reason="Clean media (unsupported format bypassed safely)",
                suggested_action=SuggestedAction.PASS_MESSAGE,
                evidence_frame_bytes=None,
            )

        # 3. Inspect Frames (QR -> NSFW -> OCR)
        for frame in frames:
            frame_buffer = io.BytesIO()
            frame.save(frame_buffer, format="JPEG", quality=85)
            frame_bytes = frame_buffer.getvalue()

            # A. QR Code Scanner
            qr_result = QRDetector.scan_image(frame_bytes)
            if qr_result.has_qr:
                for payload in qr_result.payloads:
                    if any(kw in payload.lower() for kw in ("t.me/", "http", "crypto", "ton", "bot")):
                        logger.info(f"Suspicious QR link detected: {payload}")
                        return MediaModerationVerdict(
                            is_violation=True,
                            category=ViolationCategory.COMMERCIAL_AD,
                            confidence=95.0,
                            reason=f"Обнаружен QR-код со ссылкой: {payload[:60]}",
                            suggested_action=SuggestedAction.WARN,
                            evidence_frame_bytes=frame_bytes,
                        )

            # B. NSFW Local Detector
            nsfw_result = await nsfw_detector.detect(frame)
            if nsfw_result.is_nsfw:
                logger.info(f"NSFW content detected: {nsfw_result.detected_classes}")
                if phash_str:
                    await PHashDeduplicator.register_spam_hash(phash_str)
                return MediaModerationVerdict(
                    is_violation=True,
                    category=ViolationCategory.ADULT_NSFW,
                    confidence=nsfw_result.confidence,
                    reason="Обнаружен неприемлемый или порнографический контент",
                    suggested_action=SuggestedAction.BAN_USER,
                    evidence_frame_bytes=frame_bytes,
                )

            # C. OCR Text Scanner
            ocr_result = OCREngine.scan_image(frame)
            if ocr_result.has_text and ocr_result.sanitized.extracted_urls:
                logger.info("OCR detected URLs inside image banner")
                return MediaModerationVerdict(
                    is_violation=True,
                    category=ViolationCategory.COMMERCIAL_AD,
                    confidence=90.0,
                    reason="Обнаружен рекламный баннер со скрытыми ссылками",
                    suggested_action=SuggestedAction.WARN,
                    evidence_frame_bytes=frame_bytes,
                )

        # 4. Clean Frames Cleanup
        # All frames discarded from memory automatically
        return MediaModerationVerdict(
            is_violation=False,
            category=ViolationCategory.CLEAN,
            confidence=0.0,
            reason="Media passed all local safety checks",
            suggested_action=SuggestedAction.PASS_MESSAGE,
            evidence_frame_bytes=None,
        )
