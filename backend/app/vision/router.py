# app/vision/router.py
from __future__ import annotations

from app.vision.config import VisionConfig
from app.vision.providers.base import VisionProvider
from app.vision.providers.gemini_provider import GeminiVisionProvider



def get_provider(cfg: VisionConfig) -> VisionProvider:
    if cfg.provider == "gemini":
        return GeminiVisionProvider(cfg)

    raise ValueError(f"Unknown VISION_PROVIDER: {cfg.provider}")
