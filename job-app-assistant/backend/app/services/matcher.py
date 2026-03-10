"""Skill and keyword matching for job scoring."""
import re
from dataclasses import dataclass
from typing import Optional

from app.models.schemas import Job, Profile


def _strip_html(text: str) -> str:
    """Remove HTML tags for cleaner matching."""
    return re.sub(r"<[^>]+>", " ", text)


@dataclass
class ScoredJob:
    """Job with match score and matched terms."""

    job: Job
    score: float
    matched_skills: list[str]
    matched_keywords: list[str]


def _normalize(text: str) -> str:
    """Lowercase and normalize for matching."""
    return text.lower().strip()


def _tokenize(text: str) -> set[str]:
    """Extract words from text for matching."""
    normalized = _normalize(text)
    # Keep alphanumeric and common separators, split on non-word
    words = re.findall(r"[a-z0-9]+", normalized)
    return set(w for w in words if len(w) > 1)


def _normalize_skill(skill: str) -> set[str]:
    """Normalize a skill for matching (e.g. 'Kubernetes' -> {'kubernetes'})."""
    return _tokenize(skill)


def score_job(
    job: Job,
    skills: list[str],
    keywords: list[str],
    location_terms: Optional[list[str]] = None,
) -> ScoredJob:
    """Score a job based on skill, keyword, and location overlap."""
    desc_clean = _strip_html(job.description)
    desc_tokens = _tokenize(desc_clean)
    title_tokens = _tokenize(job.title)
    loc_tokens = _tokenize(job.location)
    all_job_tokens = desc_tokens | title_tokens | loc_tokens

    matched_skills: list[str] = []
    matched_keywords: list[str] = []

    for skill in skills:
        skill_tokens = _normalize_skill(skill)
        if skill_tokens and (skill_tokens & all_job_tokens):
            matched_skills.append(skill)

    for kw in keywords:
        kw_tokens = _tokenize(kw)
        if kw_tokens and (kw_tokens & all_job_tokens):
            matched_keywords.append(kw)

    # Location match bonus
    location_matches = 0
    if location_terms:
        for lt in location_terms:
            lt_tokens = _tokenize(lt)
            if lt_tokens and (lt_tokens & loc_tokens):
                location_matches += 1
                break  # count each location term once

    # Score: skills + keywords + location bonus
    skill_score = len(matched_skills) * 2.0
    keyword_score = len(matched_keywords) * 1.0
    location_score = location_matches * 1.5 if location_terms else 0

    max_possible = max(1, len(skills) * 2 + len(keywords) + (len(location_terms) or 0))
    raw_score = skill_score + keyword_score + location_score
    score = min(1.0, raw_score / max(10, max_possible)) * 100

    # If no skills/keywords provided, give a baseline score
    if not skills and not keywords:
        score = 50.0

    return ScoredJob(
        job=job,
        score=round(score, 1),
        matched_skills=matched_skills,
        matched_keywords=matched_keywords,
    )


def _job_matches_any_keyword(job: Job, keywords: list[str]) -> bool:
    """True if job title or description contains any keyword."""
    if not keywords:
        return True
    desc_clean = _strip_html(job.description)
    text = (job.title + " " + desc_clean).lower()
    for kw in keywords:
        if kw.strip() and kw.strip().lower() in text:
            return True
    # Also check token overlap
    text_tokens = _tokenize(job.title + " " + desc_clean)
    for kw in keywords:
        kw_tokens = _tokenize(kw)
        if kw_tokens and (kw_tokens & text_tokens):
            return True
    return False


def rank_jobs(
    jobs: list[Job],
    skills: list[str],
    keywords: list[str],
    min_score: float = 0,
    location_terms: Optional[list[str]] = None,
    filter_non_matching: bool = True,
) -> list[ScoredJob]:
    """Score and rank jobs by match quality."""
    # Filter: when we have keywords, drop jobs from Greenhouse/Lever that don't match any
    if filter_non_matching and keywords:
        jobs = [j for j in jobs if _job_matches_any_keyword(j, keywords)]

    scored = [score_job(j, skills, keywords, location_terms) for j in jobs]
    scored = [s for s in scored if s.score >= min_score]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def skills_from_profile(profile: Optional[Profile]) -> list[str]:
    """Extract skills list from profile for matching."""
    if not profile:
        return []
    return list(profile.skills)
