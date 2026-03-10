#!/bin/sh
# Run from job-app-assistant directory
cd "$(dirname "$0")"
PYTHONPATH=backend ./venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
