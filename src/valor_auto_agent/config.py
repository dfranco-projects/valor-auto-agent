from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="VALOR_", extra="ignore")

    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    # vertex ai via application default credentials (ADC) instead of a gemini api key
    google_genai_use_vertexai: bool = False
    google_cloud_project: str = ""
    google_cloud_location: str = "global"
    db_url: str = "sqlite:///data/valor.db"
    checkpoint_db: str = "data/checkpoints.db"
    headless: bool = True
    max_pages: int = 3
    max_detail_concurrency: int = 3
    snapshots_dir: Path = Path("data/snapshots")
    rater_model: str = "gemini-2.5-flash"


def load() -> Settings:
    import os

    from dotenv import load_dotenv

    # the api keys are unprefixed (ANTHROPIC_API_KEY/GEMINI_API_KEY), so pull .env into the
    # environment before the getenv fallbacks below — VALOR_-prefixed fields are read by pydantic
    load_dotenv()

    s = Settings()
    if not s.anthropic_api_key:
        s.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not s.gemini_api_key:
        s.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if not s.google_genai_use_vertexai:
        s.google_genai_use_vertexai = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in (
            "1",
            "true",
            "yes",
        )
    if not s.google_cloud_project:
        s.google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    s.google_cloud_location = os.getenv("GOOGLE_CLOUD_LOCATION", "") or s.google_cloud_location
    s.snapshots_dir.mkdir(parents=True, exist_ok=True)
    Path(s.checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
    return s
