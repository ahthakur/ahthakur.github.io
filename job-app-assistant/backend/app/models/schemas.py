"""Pydantic models for the application."""
from typing import Optional

from pydantic import BaseModel, Field


class Job(BaseModel):
    """Normalized job listing from any source."""

    title: str
    company: str
    url: str
    description: str = ""
    location: str = ""
    posted_at: Optional[str] = None
    source: str = ""
    raw: Optional[dict] = Field(default=None, exclude=True)


class Profile(BaseModel):
    """Parsed resume profile."""

    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    location: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    raw_text: str = ""
