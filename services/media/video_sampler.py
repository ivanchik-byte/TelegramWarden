"""In-memory video keyframe extraction using PyAV (0 tokens on CPU)."""

import io
from PIL import Image
import av
from core.logger import logger

# Fractions of the timeline sampled for inspection
SAMPLE_FRACTIONS = [0.05, 0.25, 0.50, 0.75, 0.95]


class VideoKeyframeSampler:
    """Extracts distributed keyframes across the timeline of a video or video note."""

    @classmethod
    def sample_keyframes(
        cls,
        video_bytes: bytes,
        num_frames: int = 5,
        target_size: tuple[int, int] = (640, 640),
    ) -> list[Image.Image]:
        """Extract evenly distributed small PIL Images across the video timeline.

        Frames are down-scaled immediately upon decode so raw YUV frames never
        accumulate (a long video held raw would consume hundreds of MB).
        """
        if not video_bytes:
            return []

        frames: list[Image.Image] = []
        try:
            container = av.open(io.BytesIO(video_bytes))
        except Exception as err:
            logger.warning(f"Video container open failed: {err}")
            return []

        try:
            video_stream = next((s for s in container.streams if s.type == "video"), None)
            if not video_stream:
                logger.warning("No video stream found in container")
                return []

            duration = video_stream.duration
            fractions = SAMPLE_FRACTIONS[:num_frames]

            # Preferred path: seek to timeline positions
            if duration and duration > 0:
                target_pts_list = [int(duration * fraction) for fraction in fractions]
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

            # Fallback when seeking unsupported: sequential decode keeping only
            # down-scaled thumbnails (bounded memory), then pick sampled indices
            if not frames:
                all_thumbs: list[Image.Image] = []
                for frame in container.decode(video_stream):
                    thumb = frame.to_image()
                    thumb.thumbnail(target_size)
                    all_thumbs.append(thumb)
                    if len(all_thumbs) >= 150:  # hard cap against pathological streams
                        break
                if all_thumbs:
                    total_count = len(all_thumbs)
                    frames = [
                        all_thumbs[min(int(total_count * fraction), total_count - 1)]
                        for fraction in fractions
                    ]

            return frames
        except Exception as err:
            logger.warning(f"Video keyframe sampling error: {err}")
            return frames
        finally:
            container.close()
