"""Job Application Assistant - FastAPI entry point."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import router

# Project root for static files
PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="Job Application Assistant",
    description="ToS-compliant job discovery and profile management for faster applications",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["api"])


@app.get("/")
async def root():
    """Serve dashboard."""
    dashboard = PROJECT_ROOT / "frontend" / "index.html"
    if dashboard.exists():
        return FileResponse(dashboard)
    return {"message": "Job Application Assistant API", "docs": "/docs"}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}
