"""Job fetcher service - Adzuna, Greenhouse, Lever APIs."""
import asyncio
from typing import Optional

import httpx

from app.models.schemas import Job

# Default company board slugs for Greenhouse (popular tech companies)
GREENHOUSE_BOARDS = [
    "stripe",
    "airbnb",
    "dropbox",
    "notion",
    "figma",
    "databricks",
    "anthropic",
    "openai",
    "discord",
    "robinhood",
    "square",
    "plaid",
    "reddit",
    "asana",
    "box",
]

# Default company IDs for Lever
LEVER_COMPANIES = [
    "netflix",
    "spotify",
    "uber",
    "lyft",
    "twitch",
    "slack",
    "coinbase",
    "hashicorp",
    "zendesk",
    "instacart",
]


class JobFetcher:
    """Fetch jobs from Adzuna, Greenhouse, and Lever."""

    def __init__(
        self,
        adzuna_app_id: str = "",
        adzuna_app_key: str = "",
        greenhouse_boards: Optional[list[str]] = None,
        lever_companies: Optional[list[str]] = None,
    ):
        self.adzuna_app_id = adzuna_app_id
        self.adzuna_app_key = adzuna_app_key
        self.greenhouse_boards = greenhouse_boards or GREENHOUSE_BOARDS
        self.lever_companies = lever_companies or LEVER_COMPANIES

    async def fetch_adzuna(
        self,
        keywords: str,
        location: str = "",
        country: str = "us",
        max_results: int = 20,
    ) -> list[Job]:
        """Fetch jobs from Adzuna API."""
        if not self.adzuna_app_id or not self.adzuna_app_key:
            return []

        jobs: list[Job] = []
        page = 1
        per_page = min(20, max_results)

        async with httpx.AsyncClient(timeout=15.0) as client:
            while len(jobs) < max_results:
                url = (
                    f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
                    f"?app_id={self.adzuna_app_id}&app_key={self.adzuna_app_key}"
                    f"&what={keywords}&results_per_page={per_page}"
                )
                if location:
                    url += f"&where={location}"

                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                except (httpx.HTTPError, ValueError):
                    break

                results = data.get("results", [])
                if not results:
                    break

                for r in results:
                    jobs.append(
                        Job(
                            title=r.get("title", ""),
                            company=r.get("company", {}).get("display_name", ""),
                            url=r.get("redirect_url", ""),
                            description=r.get("description", ""),
                            location=r.get("location", {}).get("display_name", ""),
                            posted_at=r.get("created"),
                            source="adzuna",
                        )
                    )
                    if len(jobs) >= max_results:
                        break

                page += 1
                if page > data.get("page_count", 1):
                    break

        return jobs[:max_results]

    async def fetch_greenhouse(self, max_per_board: int = 5) -> list[Job]:
        """Fetch jobs from Greenhouse public boards."""
        jobs: list[Job] = []
        sem = asyncio.Semaphore(5)

        async def fetch_board(client: httpx.AsyncClient, board: str) -> list[Job]:
            async with sem:
                try:
                    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
                    resp = await client.get(url, timeout=10.0)
                    resp.raise_for_status()
                    data = resp.json()
                except (httpx.HTTPError, ValueError):
                    return []

                board_jobs: list[Job] = []
                for j in data.get("jobs", [])[:max_per_board]:
                    board_jobs.append(
                        Job(
                            title=j.get("title", ""),
                            company=data.get("meta", {}).get("company_name", board),
                            url=j.get("absolute_url", ""),
                            description=j.get("content", ""),
                            location=", ".join(
                                loc.get("name", "") for loc in j.get("locations", [])
                            ),
                            posted_at=j.get("updated_at"),
                            source="greenhouse",
                        )
                    )
                return board_jobs

        async with httpx.AsyncClient() as client:
            tasks = [fetch_board(client, b) for b in self.greenhouse_boards]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    jobs.extend(r)
                # Skip exceptions

        return jobs

    async def fetch_lever(self, max_per_company: int = 5) -> list[Job]:
        """Fetch jobs from Lever public API."""
        jobs: list[Job] = []
        sem = asyncio.Semaphore(5)

        async def fetch_company(
            client: httpx.AsyncClient, company: str
        ) -> list[Job]:
            async with sem:
                try:
                    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
                    resp = await client.get(url, timeout=10.0)
                    resp.raise_for_status()
                    data = resp.json()
                except (httpx.HTTPError, ValueError):
                    return []

                company_jobs: list[Job] = []
                for j in data[:max_per_company]:
                    company_jobs.append(
                        Job(
                            title=j.get("text", ""),
                            company=j.get("categories", {}).get("team", company),
                            url=j.get("hostedUrl", ""),
                            description=j.get("description", ""),
                            location=", ".join(j.get("categories", {}).get("location", []) or []),
                            posted_at=j.get("createdAt"),
                            source="lever",
                        )
                    )
                return company_jobs

        async with httpx.AsyncClient() as client:
            tasks = [fetch_company(client, c) for c in self.lever_companies]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    jobs.extend(r)

        return jobs

    async def fetch_all(
        self,
        keywords: str = "",
        location: str = "",
        include_adzuna: bool = True,
        include_greenhouse: bool = True,
        include_lever: bool = True,
        max_results: int = 50,
    ) -> list[Job]:
        """Fetch from all configured sources and merge."""
        tasks = []
        if include_adzuna and self.adzuna_app_id and keywords:
            tasks.append(
                self.fetch_adzuna(keywords, location, max_results=max_results)
            )
        if include_greenhouse:
            tasks.append(self.fetch_greenhouse(max_per_board=3))
        if include_lever:
            tasks.append(self.fetch_lever(max_per_company=3))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        jobs: list[Job] = []
        for r in results:
            if isinstance(r, list):
                jobs.extend(r)
        return jobs[:max_results]
