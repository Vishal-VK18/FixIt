"""Compatibility checks for the legacy vision entry point."""

import pytest
import vision
import config
from openrouter_client import OpenRouterError


def test_vision_compatibility_path_requires_real_provider_key(monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", None)
    with pytest.raises(OpenRouterError, match="Set OPENROUTER_API_KEY"):
        vision.analyze_image(b"not-an-image", "image/jpeg")
