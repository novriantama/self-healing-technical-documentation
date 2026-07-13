# pyrefly: ignore [missing-import]
from src.config import Settings


def test_settings_load_from_env():
    settings = Settings()
    assert settings.anthropic_api_key == "mock-anthropic-key"
    assert settings.confidence_threshold == 0.8
