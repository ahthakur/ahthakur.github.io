"""Application configuration."""
import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    user_config_path: str = "config/user_config.yaml"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "env_nested_delimiter": "__",
    }

    @property
    def adzuna_configured(self) -> bool:
        """Check if Adzuna API is configured."""
        return bool(self.adzuna_app_id and self.adzuna_app_key)


def get_config_path() -> Path:
    """Resolve user config path relative to project root."""
    path = os.getenv("USER_CONFIG_PATH", "config/user_config.yaml")
    # If relative, resolve from job-app-assistant root
    base = Path(__file__).resolve().parent.parent.parent
    return base / path if not Path(path).is_absolute() else Path(path)
