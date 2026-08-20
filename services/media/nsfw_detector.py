"""Local CPU-based NSFW and Adult Content Detector using ONNX Runtime (0 tokens)."""

import asyncio
import io
from pathlib import Path
from typing import NamedTuple, Optional
import numpy as np
from PIL import Image
import onnxruntime as ort
from core.logger import logger

MODELS_DIR = Path("models_cache")
NSFW_MODEL_PATH = MODELS_DIR / "nsfw_detector_320.onnx"


class NSFWDetectionResult(NamedTuple):
    """Result container for NSFW image inspection."""

    is_nsfw: bool
    confidence: float
    detected_classes: list[str]


class NSFWDetector:
    """Runs local ONNX inference on CPU to classify adult/NSFW content."""

    def __init__(self, model_path: Path = NSFW_MODEL_PATH) -> None:
        self.model_path = model_path
        self._session: Optional[ort.InferenceSession] = None
        self._is_initialized = False

    def _init_session(self) -> bool:
        """Initialize the ONNX Runtime Inference Session on CPU."""
        if self._is_initialized:
            return self._session is not None

        if not self.model_path.exists():
            logger.debug(f"NSFW ONNX model not found at {self.model_path}. Will use safe fallback.")
            self._is_initialized = True
            return False

        try:
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = 2
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

            self._session = ort.InferenceSession(
                str(self.model_path),
                sess_options=sess_options,
                providers=["CPUExecutionProvider"],
            )
            self._is_initialized = True
            logger.info(f"Loaded NSFW ONNX Model from {self.model_path}")
            return True
        except Exception as err:
            logger.error(f"Failed to load NSFW ONNX model: {err}")
            self._is_initialized = True
            return False

    @classmethod
    def _preprocess_image(cls, pil_img: Image.Image, target_size: tuple[int, int] = (320, 320)) -> np.ndarray:
        """Preprocess PIL Image to normalized float32 tensor (1, 3, H, W)."""
        rgb_img = pil_img.convert("RGB").resize(target_size, Image.Resampling.BILINEAR)
        arr = np.array(rgb_img, dtype=np.float32) / 255.0

        # Standard ImageNet normalization: (x - mean) / std
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        norm_arr = (arr - mean) / std

        # Transpose from (H, W, C) to (C, H, W) and add batch dimension (1, C, H, W)
        tensor = np.transpose(norm_arr, (2, 0, 1))
        return np.expand_dims(tensor, axis=0)

    def _sync_detect(self, pil_img: Image.Image) -> NSFWDetectionResult:
        """Execute synchronous model inference on CPU."""
        if not self._init_session() or self._session is None:
            # Model file not present in test/offline environment -> safe clean default
            return NSFWDetectionResult(is_nsfw=False, confidence=0.0, detected_classes=[])

        try:
            tensor = self._preprocess_image(pil_img)
            input_name = self._session.get_inputs()[0].name
            outputs = self._session.run(None, {input_name: tensor})

            # Check output probabilities (sigmoid/softmax)
            raw_scores = outputs[0]
            if len(raw_scores.shape) == 2 and raw_scores.shape[1] >= 2:
                # Binary / Multiclass probabilities [Safe, NSFW]
                nsfw_prob = float(raw_scores[0][1])
                is_nsfw = nsfw_prob > 0.80
                return NSFWDetectionResult(
                    is_nsfw=is_nsfw,
                    confidence=round(nsfw_prob * 100, 2),
                    detected_classes=["EXPOSED_CONTENT"] if is_nsfw else ["SAFE"],
                )

            return NSFWDetectionResult(is_nsfw=False, confidence=0.0, detected_classes=[])

        except Exception as err:
            logger.warning(f"ONNX NSFW inference error: {err}")
            return NSFWDetectionResult(is_nsfw=False, confidence=0.0, detected_classes=[])

    async def detect(self, pil_img: Image.Image) -> NSFWDetectionResult:
        """Asynchronously run CPU inference in thread pool without blocking event loop."""
        return await asyncio.to_thread(self._sync_detect, pil_img)


# Global NSFW detector singleton
nsfw_detector = NSFWDetector()
