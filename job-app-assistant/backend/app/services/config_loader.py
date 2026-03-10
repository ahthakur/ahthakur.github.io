"""Load and validate user configuration from YAML."""
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class UserConfig(BaseModel):
    """User configuration schema."""

    resume_url: str = ""
    keywords: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)

    @property
    def has_resume(self) -> bool:
        return bool(self.resume_url.strip())

    @property
    def search_keywords(self) -> str:
        """Join keywords for API search."""
        return " ".join(self.keywords) if self.keywords else ""

    @property
    def location_str(self) -> str:
        return ", ".join(self.locations) if self.locations else ""


def load_user_config(path: Path) -> Optional[UserConfig]:
    """Load user config from YAML file."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        return UserConfig(**data) if data else UserConfig()
    except Exception:
        return None
