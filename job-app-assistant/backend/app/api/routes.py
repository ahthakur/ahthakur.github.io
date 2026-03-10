"""FastAPI routes."""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import get_config_path
from app.models.schemas import Job, Profile
from app.services.config_loader import load_user_config
from app.services.job_fetcher import JobFetcher
from app.services.matcher import rank_jobs, skills_from_profile
from app.services.resume_parser import parse_resume_content

router = APIRouter()

# In-memory cache for profile (single-user v1)
_profile_cache: Optional[Profile] = None


class JobsResponse(BaseModel):
    """Jobs response with scores."""

    jobs: list[dict]
    total: int


class ProfileResponse(BaseModel):
    """Profile response."""

    profile: dict


class ProfileAnswersResponse(BaseModel):
    """Profile answers for copy-paste."""

    name: str
    email: str
    phone: str
    linkedin: str
    location: str
    skills: list[str]
    experience_summary: str
    education_summary: str


def _get_job_fetcher():
    """Create JobFetcher with settings."""
    from app.config import Settings

    s = Settings()
    return JobFetcher(
        adzuna_app_id=s.adzuna_app_id,
        adzuna_app_key=s.adzuna_app_key,
    )


def _parse_keywords(s: str) -> list[str]:
    """Split keywords by comma, strip, keep non-empty."""
    if not s or not s.strip():
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


@router.get("/jobs")
async def get_jobs(
    keywords: Optional[str] = None,
    location: Optional[str] = None,
    min_score: float = 0,
) -> JobsResponse:
    """Fetch jobs from APIs, match by skills/keywords, return ranked list."""
    config_path = get_config_path()
    user_config = load_user_config(config_path)

    kw = keywords or (user_config.search_keywords if user_config else "") or "software"
    loc = location or (user_config.location_str if user_config else "")

    # Use search keywords for matching (so results are scored by relevance)
    request_keywords = _parse_keywords(kw)

    # Skills: from parsed profile first, then config
    skills = list(skills_from_profile(_profile_cache)) if _profile_cache else []
    if user_config and user_config.skills:
        skills = list(dict.fromkeys(skills + user_config.skills))

    # Match keywords: request keywords + config keywords
    match_keywords = list(dict.fromkeys(request_keywords + (user_config.keywords if user_config else [])))

    # Location terms for matching (e.g. "Austin, Remote" -> ["Austin", "Remote"])
    location_terms = _parse_keywords(loc)

    fetcher = _get_job_fetcher()
    jobs = await fetcher.fetch_all(
        keywords=kw,
        location=loc,
        max_results=80,
    )

    scored = rank_jobs(
        jobs, skills, match_keywords,
        min_score=min_score,
        location_terms=location_terms,
        filter_non_matching=False,
    )

    return JobsResponse(
        jobs=[
            {
                "title": s.job.title,
                "company": s.job.company,
                "url": s.job.url,
                "description": s.job.description[:500] + "..." if len(s.job.description) > 500 else s.job.description,
                "location": s.job.location,
                "posted_at": s.job.posted_at,
                "source": s.job.source,
                "score": s.score,
                "matched_skills": s.matched_skills,
                "matched_keywords": s.matched_keywords,
            }
            for s in scored
        ],
        total=len(scored),
    )


@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)) -> ProfileResponse:
    """
    Upload and parse a resume PDF or Markdown file.
    Accepts multipart/form-data with field name 'file'.
    """
    global _profile_cache

    content = await file.read()
    if len(content) < 50:
        raise HTTPException(status_code=400, detail="File too small or empty")

    ext = (file.filename or "").lower()
    if ext.endswith((".md", ".markdown")):
        content_type = "md"
    else:
        content_type = "pdf"

    try:
        profile = parse_resume_content(content, content_type)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {str(e)}")

    _profile_cache = profile
    return ProfileResponse(profile=profile.model_dump())


@router.get("/profile")
async def get_profile() -> ProfileResponse:
    """Return cached profile from last parse."""
    global _profile_cache
    if _profile_cache is None:
        raise HTTPException(status_code=404, detail="No profile cached. POST to /parse-resume first.")
    return ProfileResponse(profile=_profile_cache.model_dump())


@router.get("/profile/answers")
async def get_profile_answers() -> ProfileAnswersResponse:
    """Return profile data formatted for copy-paste into job applications."""
    global _profile_cache
    if _profile_cache is None:
        raise HTTPException(status_code=404, detail="No profile cached. POST to /parse-resume first.")

    p = _profile_cache
    exp_summary = "\n".join(p.experience[:5]) if p.experience else ""
    edu_summary = "\n".join(p.education[:3]) if p.education else ""

    return ProfileAnswersResponse(
        name=p.name,
        email=p.email,
        phone=p.phone,
        linkedin=p.linkedin,
        location=p.location,
        skills=p.skills,
        experience_summary=exp_summary,
        education_summary=edu_summary,
    )
