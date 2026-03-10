"""Resume parser - fetch from URL and extract structured data."""
import re
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpx

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # type: ignore

from app.models.schemas import Profile

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)
PHONE_PATTERN = re.compile(
    r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}"
)
LINKEDIN_PATTERN = re.compile(
    r"(?:linkedin\.com/in/|LinkedIn\s*[:\s]*)([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)


def _extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF bytes."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF parsing. Install with: pip install PyMuPDF")
    doc = fitz.open(stream=content, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def _parse_markdown(content: str) -> str:
    """Return markdown content as-is for parsing (headers/bullets preserved)."""
    return content


def _extract_name(lines: list[str]) -> str:
    """Heuristic: first non-empty line is often the name."""
    for line in lines:
        line = line.strip()
        if not line or len(line) > 80:
            continue
        if "@" in line or "linkedin" in line.lower() or line.lower().startswith("http"):
            continue
        if re.match(r"^\d", line):
            continue
        return line
    return ""


def _extract_fields(text: str) -> Profile:
    """Extract structured fields from resume text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    email = ""
    phone = ""
    linkedin = ""
    skills: list[str] = []
    experience: list[str] = []
    education: list[str] = []

    email_m = EMAIL_PATTERN.search(text)
    if email_m:
        email = email_m.group(0)

    phone_m = PHONE_PATTERN.search(text)
    if phone_m:
        phone = phone_m.group(0)

    linkedin_m = LINKEDIN_PATTERN.search(text)
    if linkedin_m:
        linkedin = f"https://linkedin.com/in/{linkedin_m.group(1)}"

    name = _extract_name(lines)

    # Skills: look for common section headers
    in_skills = False
    in_experience = False
    in_education = False
    skill_headers = ("skills", "expertise", "technical", "areas of")
    exp_headers = ("experience", "work experience", "employment", "professional")
    edu_headers = ("education", "academic", "qualifications")

    for i, line in enumerate(lines):
        lower = line.lower()
        if any(h in lower for h in skill_headers) and len(line) < 50:
            in_skills = True
            in_experience = False
            in_education = False
            continue
        if any(h in lower for h in exp_headers) and len(line) < 50:
            in_experience = True
            in_skills = False
            in_education = False
            continue
        if any(h in lower for h in edu_headers) and len(line) < 50:
            in_education = True
            in_skills = False
            in_experience = False
            continue

        if in_skills and line and not line.startswith("#") and len(line) < 100:
            # Bullet or comma-separated skills
            parts = re.split(r"[,•\-\*\|]", line)
            for p in parts:
                p = p.strip()
                if p and len(p) > 1 and len(p) < 50:
                    skills.append(p)
        if in_experience and line:
            if line.startswith(("•", "-", "*", "–")) or re.match(r"^\d+\.", line):
                experience.append(line.lstrip("•-*– ").lstrip("0123456789.) "))
            elif line and len(line) > 20 and not line.endswith(":"):
                experience.append(line)
        if in_education and line:
            if "university" in lower or "college" in lower or "bachelor" in lower or "master" in lower or "degree" in lower or "ms" in lower or "bs" in lower:
                education.append(line)

    return Profile(
        name=name,
        email=email,
        phone=phone,
        linkedin=linkedin,
        location="",
        skills=list(dict.fromkeys(skills))[:50],
        experience=experience[:30],
        education=education[:10],
        raw_text=text[:10000],
    )


async def fetch_resume_from_url(url: str) -> bytes:
    """Fetch resume content from URL (e.g. GitHub raw URL)."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


def parse_resume_content(content: bytes, content_type: str = "pdf") -> Profile:
    """Parse resume content and return structured Profile."""
    if content_type.lower() in ("pdf", "application/pdf"):
        text = _extract_text_from_pdf(content)
    elif content_type.lower() in ("md", "markdown", "text/markdown", "text/plain"):
        text = content.decode("utf-8", errors="replace")
    else:
        # Try PDF first, fall back to text
        try:
            text = _extract_text_from_pdf(content)
        except Exception:
            text = content.decode("utf-8", errors="replace")
    return _extract_fields(text)


def infer_content_type(url: str) -> str:
    """Infer content type from URL."""
    url_lower = url.lower()
    if url_lower.endswith(".pdf"):
        return "pdf"
    if url_lower.endswith((".md", ".markdown")):
        return "md"
    return "pdf"  # Default


def _to_raw_github_url(url: str) -> str:
    """Convert github.com blob URL to raw.githubusercontent.com URL."""
    if "github.com" in url and "/blob/" in url:
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    return url


def _read_local_file(path: str) -> bytes:
    """Read resume from local file path."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise ValueError(f"Local file not found: {path}")
    if not p.is_file():
        raise ValueError(f"Not a file: {path}")
    return p.read_bytes()


async def parse_resume_from_url(url: str) -> Profile:
    """Fetch resume from URL or local file path and parse into Profile."""
    url = url.strip()

    # Handle local file: file:// path or path that doesn't look like HTTP
    if url.startswith("file://"):
        path = url[7:]
        content = _read_local_file(path)
        content_type = infer_content_type(path)
        return parse_resume_content(content, content_type)

    # Check if it's a local path (exists on disk, doesn't start with http)
    if not url.startswith(("http://", "https://")):
        try:
            content = _read_local_file(url)
            content_type = infer_content_type(url)
            return parse_resume_content(content, content_type)
        except ValueError:
            pass  # Fall through - maybe they meant something else

    url = _to_raw_github_url(url)
    try:
        content = await fetch_resume_from_url(url)
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"Failed to fetch resume: HTTP {e.response.status_code}. "
            "For GitHub, use raw URL: https://raw.githubusercontent.com/user/repo/branch/file.pdf"
        ) from e
    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch resume: {e}") from e

    if not content or len(content) < 50:
        raise ValueError("Resume file is empty or too small")

    # Detect if we got HTML instead of PDF (e.g. wrong GitHub URL)
    if url.lower().endswith(".pdf") and not content.startswith(b"%PDF"):
        raise ValueError(
            "URL returned HTML, not a PDF. Use the raw GitHub URL: "
            "https://raw.githubusercontent.com/username/repo/branch/resume.pdf"
        )

    content_type = infer_content_type(url)
    try:
        return parse_resume_content(content, content_type)
    except Exception as e:
        raise ValueError(f"Failed to parse resume: {e}") from e
