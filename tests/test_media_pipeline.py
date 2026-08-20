"""Unit tests for MediaModerationPipeline, QR detection, pHash, and VideoKeyframeSampler."""

import io
import pytest
from unittest.mock import AsyncMock, patch
import numpy as np
from PIL import Image
import av

from services.ai.schema import SuggestedAction, ViolationCategory
from services.media.phash import PHashDeduplicator
from services.media.qr_detector import QRDetector
from services.media.video_sampler import VideoKeyframeSampler
from services.media.pipeline import MediaModerationPipeline


def create_synthetic_image(color=(255, 0, 0), size=(200, 200)) -> bytes:
    """Helper to generate in-memory synthetic JPEG image bytes."""
    img = Image.new("RGB", size, color=color)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def create_synthetic_video_bytes(num_frames: int = 15, size: tuple[int, int] = (128, 128)) -> bytes:
    """Helper to generate in-memory synthetic MP4 video container bytes using PyAV."""
    buffer = io.BytesIO()
    container = av.open(buffer, mode="w", format="mp4")
    stream = container.add_stream("mpeg4", rate=10)
    stream.width = size[0]
    stream.height = size[1]
    stream.pix_fmt = "yuv420p"

    for i in range(num_frames):
        # Create an animated synthetic frame
        arr = np.full((size[1], size[0], 3), (i * 15) % 255, dtype=np.uint8)
        frame = av.VideoFrame.from_ndarray(arr, format="rgb24")
        for packet in stream.encode(frame):
            container.mux(packet)

    for packet in stream.encode():
        container.mux(packet)

    container.close()
    return buffer.getvalue()


def test_phash_computation_consistency():
    """Verify that pHash produces consistent 16-character hex string for identical images."""
    img_bytes = create_synthetic_image(color=(100, 150, 200))
    hash1 = PHashDeduplicator.compute_hash(img_bytes)
    hash2 = PHashDeduplicator.compute_hash(img_bytes)

    assert hash1 is not None
    assert hash1 == hash2
    assert len(hash1) == 16


def test_video_keyframe_sampler_extracts_frames():
    """Verify that VideoKeyframeSampler extracts distributed keyframes from video container."""
    video_bytes = create_synthetic_video_bytes(num_frames=20)
    keyframes = VideoKeyframeSampler.sample_keyframes(video_bytes, num_frames=5)

    assert len(keyframes) >= 1
    assert all(isinstance(f, Image.Image) for f in keyframes)


@pytest.mark.asyncio
async def test_media_pipeline_clean_image_passes():
    """Verify that clean image passes all filters with no violations."""
    clean_bytes = create_synthetic_image(color=(200, 200, 200))

    with patch("services.media.pipeline.PHashDeduplicator.is_known_spam", AsyncMock(return_value=False)):
        verdict = await MediaModerationPipeline.process_media(clean_bytes, media_type="photo")

        assert verdict.is_violation is False
        assert verdict.category == ViolationCategory.CLEAN
        assert verdict.suggested_action == SuggestedAction.PASS_MESSAGE
        assert verdict.evidence_frame_bytes is None


@pytest.mark.asyncio
async def test_media_pipeline_catches_nsfw_mock():
    """Verify that pipeline catches NSFW violation and retains evidence frame."""
    fake_nsfw_bytes = create_synthetic_image(color=(255, 50, 50))

    with patch("services.media.pipeline.PHashDeduplicator.is_known_spam", AsyncMock(return_value=False)), \
         patch("services.media.pipeline.PHashDeduplicator.register_spam_hash", AsyncMock()), \
         patch("services.media.pipeline.nsfw_detector.detect") as mock_detect:
        from services.media.nsfw_detector import NSFWDetectionResult
        mock_detect.return_value = NSFWDetectionResult(
            is_nsfw=True,
            confidence=96.4,
            detected_classes=["EXPOSED_GENITALIA"],
        )

        verdict = await MediaModerationPipeline.process_media(fake_nsfw_bytes, media_type="photo")

        assert verdict.is_violation is True
        assert verdict.category == ViolationCategory.ADULT_NSFW
        assert verdict.confidence == 96.4
        assert verdict.suggested_action == SuggestedAction.BAN_USER
        assert verdict.evidence_frame_bytes is not None
