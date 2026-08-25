"""Unified Media Moderation Pipeline orchestrating QR, pHash, NSFW, and OCR."""

import asyncio
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

# Magic-byte signatures for content-based media type detection. Declared MIME
# types are attacker-controlled; what matters is what the bytes actually are.
def sniff_media_kind(data: bytes) -> Optional[str]:
    """Detect real media kind from magic bytes: 'photo', 'video' or None."""
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "photo"  # JPEG
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "photo"  # PNG
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "animation"  # GIF
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "photo"  # WebP
    if data[4:8] == b"ftyp":
        return "video"  # MP4/MOV family (incl. HEIC containers)
    if data[:4] == b"\x1aE\xdf\xa3":
        return "video"  # WebM/MKV
    if data[:2] == b"BM":
        return "photo"  # BMP
    return None


class MediaModerationVerdict(NamedTuple):
    """Result of media file inspection."""

    is_violation: bool
    category: ViolationCategory
    confidence: float
    reason: str
    suggested_action: SuggestedAction
    evidence_frame_bytes: Optional[bytes]
    # True when the hit comes from soft signals (QR/OCR) that must be
    # confirmed by an admin instead of triggering automatic sanctions.
    requires_admin_review: bool = False
    # True only when the NSFW model actually ran over at least one frame.
    # Callers may apply fail-closed policies when this is False.
    nsfw_checked: bool = False


class MediaModerationPipeline:
    """Orchestrates all media scanning steps with zero unnecessary token costs."""

    @classmethod
    async def process_media(
        cls,
        media_bytes: bytes,
        media_type: str = "photo",  # 'photo', 'video', 'video_note', 'sticker', 'animation'
        scan_nsfw: bool = True,
        scan_qr: bool = True,
        scan_ocr: bool = True,
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

        # 1. pHash Spam Check (~1 ms, CPU-bound -> thread pool)
        phash_str = await asyncio.to_thread(PHashDeduplicator.compute_hash, media_bytes)
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

        # 2. Frame Extraction (CPU-bound decode -> thread pool; PyAV can take
        # seconds and must never freeze the event loop)
        frames: list[Image.Image] = []
        if media_type in ("video", "video_note", "animation"):
            # Telegram .animation is an MP4/GIF hybrid: PyAV decodes both
            frames = await asyncio.to_thread(
                VideoKeyframeSampler.sample_keyframes, media_bytes, 5
            )
        else:
            def _decode_image() -> list[Image.Image]:
                try:
                    with Image.open(io.BytesIO(media_bytes)) as pil_img:
                        return [pil_img.convert("RGB")]
                except Exception as err:
                    logger.warning(f"Failed to open image bytes: {err}")
                    return []

            frames = await asyncio.to_thread(_decode_image)

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

        # 3. Inspect Frames — NSFW first across ALL frames, then soft signals,
        # so a QR code on an early frame cannot short-circuit a porn verdict.
        encoded_frames: list[tuple[Image.Image, bytes]] = []
        for frame in frames:
            buffer = io.BytesIO()
            frame.save(buffer, format="JPEG", quality=85)
            encoded_frames.append((frame, buffer.getvalue()))

        # Videos cannot be hashed from raw container bytes: derive the spam
        # fingerprint from the first decoded frame instead.
        if not phash_str and encoded_frames and media_type in ("video", "video_note", "animation"):
            phash_str = await asyncio.to_thread(
                PHashDeduplicator.compute_hash, encoded_frames[0][1]
            )
            if phash_str and await PHashDeduplicator.is_known_spam(phash_str):
                logger.info("Known spam pHash detected on video keyframe")
                return MediaModerationVerdict(
                    is_violation=True,
                    category=ViolationCategory.COMMERCIAL_AD,
                    confidence=99.0,
                    reason="Обнаружен известный спам по визуальному отпечатку (pHash)",
                    suggested_action=SuggestedAction.BAN_USER,
                    evidence_frame_bytes=encoded_frames[0][1],
                )

        # A. NSFW Local Detector (hard signal, highest priority)
        nsfw_checked = False
        if scan_nsfw:
            for frame, frame_bytes in encoded_frames:
                nsfw_result = await nsfw_detector.detect(frame)
                if not nsfw_result.model_available:
                    break  # model down: do not pretend the frames were checked
                nsfw_checked = True
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
                        nsfw_checked=True,
                    )

        # B/C. QR and OCR — soft signals flagged for admin review only
        if scan_qr or scan_ocr:
            for frame, frame_bytes in encoded_frames:
                # B. QR Code Scanner: any URL-bearing QR goes to admin review,
                # never auto-sanctioned (legitimate menus/Wi-Fi/websites exist).
                if scan_qr:
                    qr_result = QRDetector.scan_image(frame_bytes)
                    if qr_result.has_qr and qr_result.payloads:
                        payload = qr_result.payloads[0]
                        logger.info(f"QR code detected in media: {payload[:60]}")
                        return MediaModerationVerdict(
                            is_violation=True,
                            category=ViolationCategory.COMMERCIAL_AD,
                            confidence=95.0,
                            reason=f"Обнаружен QR-код со ссылкой: {payload[:60]}",
                            suggested_action=SuggestedAction.WARN,
                            evidence_frame_bytes=frame_bytes,
                            requires_admin_review=True,
                        )

                # C. OCR Text Scanner (CPU-bound pytesseract -> thread pool)
                if scan_ocr:
                    ocr_result = await asyncio.to_thread(OCREngine.scan_image, frame)
                    if ocr_result.has_text and ocr_result.sanitized.extracted_urls:
                        logger.info("OCR detected URLs inside image banner")
                        return MediaModerationVerdict(
                            is_violation=True,
                            category=ViolationCategory.COMMERCIAL_AD,
                            confidence=90.0,
                            reason="Обнаружен рекламный баннер со скрытыми ссылками",
                            suggested_action=SuggestedAction.WARN,
                            evidence_frame_bytes=frame_bytes,
                            requires_admin_review=True,
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
            nsfw_checked=nsfw_checked,
        )
