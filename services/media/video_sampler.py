"""In-memory video keyframe extraction using PyAV (0 tokens on CPU)."""

import io
from typing import Optional
from PIL import Image
import av
from core.logger import logger


class VideoKeyframeSampler:
    """Extracts distributed keyframes across the timeline of a video or video note."""

    @classmethod
    def sample_keyframes(
        cls,
        video_bytes: bytes,
        num_frames: int = 5,
        target_size: tuple[int, int] = (640, 640),
    ) -> list[Image.Image]:
        """Extract evenly distributed PIL Image frames across video timeline."""
        if not video_bytes:
            return []

        frames: list[Image.Image] = []
        try:
            container = av.open(io.BytesIO(video_bytes))
            video_stream = next((s for s in container.streams if s.type == "video"), None)
            if not video_stream:
                logger.warning("No video stream found in container")
                return []

            # Determine total duration or frame count
            duration = video_stream.duration
            time_base = video_stream.time_base

            # If duration is available in time_base units
            if duration and duration > 0:
                target_pts_list = [
                    int(duration * fraction)
                    for fraction in [0.05, 0.25, 0.50, 0.75, 0.95][:num_frames]
                ]
                for pts in target_pts_list:
                    try:
                        container.seek(pts, stream=video_stream)
                        for frame in container.decode(video_stream):
                            pil_frame = frame.to_image()
                            pil_frame.thumbnail(target_size)
                            frames.append(pil_frame)
                            break
                    except Exception as seek_err:
                        logger.debug(f"Seek failed for pts {pts}: {seek_err}")

            # Fallback if seeking is unsupported or duration is unavailable: decode sequentially
            if not frames:
                all_decoded = []
                for frame in container.decode(video_stream):
                    all_decoded.append(frame)
                    if len(all_decoded) > 100:  # Cap max frames to prevent memory spikes
                        break

                if all_decoded:
                    total_count = len(all_decoded)
                    indices = [
                        int(total_count * fraction)
                        for fraction in [0.05, 0.25, 0.50, 0.75, 0.95][:num_frames]
                    ]
                    for idx in indices:
                        clamped_idx = min(idx, total_count - 1)
                        pil_frame = all_decoded[clamped_idx].to_image()
                        pil_frame.thumbnail(target_size)
                        frames.append(pil_frame)

            container.close()
            return frames

        except Exception as err:
            logger.warning(f"Video keyframe sampling error: {err}")
            return frames
