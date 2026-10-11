from app.core.config import settings


def test_settings_loaded():
    assert settings.PROJECT_NAME == "DocForge"
    assert settings.VERSION == "0.1.0"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert "postgresql+asyncpg://" in settings.DATABASE_URL
    assert settings.REDIS_URL.startswith("redis://")
    assert settings.STORAGE_BUCKET_INPUTS == "docforge-inputs"
