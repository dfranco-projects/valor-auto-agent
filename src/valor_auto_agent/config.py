from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="VALOR_", extra="ignore")

    anthropic_api_key: str = ""
    db_url: str = "sqlite:///data/valor.db"
    checkpoint_db: str = "data/checkpoints.db"
    headless: bool = True
    max_pages: int = 3
    max_detail_concurrency: int = 3
    snapshots_dir: Path = Path("data/snapshots")
    rater_model: str = "claude-sonnet-4-6"


def load() -> Settings:
    import os

    s = Settings()
    if not s.anthropic_api_key:
        s.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    s.snapshots_dir.mkdir(parents=True, exist_ok=True)
    Path(s.checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
    return s
