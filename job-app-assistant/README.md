# Job Application Assistant using cursor

A **ToS-compliant** job discovery and profile tool that helps you find jobs from Adzuna, Greenhouse, and Lever, match them to your skills, and quickly copy your profile data for applications. No scraping—uses official APIs only.

## Features

- **Job discovery** from Adzuna, Greenhouse, and Lever (legal APIs)
- **Resume parsing** from GitHub raw URL (PDF or Markdown)
- **Skill matching** to rank jobs by relevance
- **Profile copy-paste** for fast form filling (name, email, LinkedIn, skills)
- **Multi-user ready** via YAML config (resume URL, keywords, skills)

## Quick Start

### 1. Clone and setup

```bash
cd job-app-assistant
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get API keys (optional but recommended)

- **Adzuna** (free): [developer.adzuna.com](https://developer.adzuna.com)
  - Create an account, get App ID and App Key
- **Greenhouse & Lever**: No keys needed (public job boards)

### 3. Configure

```bash
cp .env.example .env
# Edit .env and add:
# ADZUNA_APP_ID=your_app_id
# ADZUNA_APP_KEY=your_app_key
```

For default keywords and skills, copy and edit the user config:

```bash
cp config/user_config.example.yaml config/user_config.yaml
# Edit with your resume URL, keywords, and skills
```

### 4. Run

```bash
cd job-app-assistant
PYTHONPATH=backend ./venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the run script: `./run.sh`

Open [http://localhost:8000](http://localhost:8000) for the dashboard. **Important:** Use this URL—if you open the HTML file directly (file://) or via another server, the API calls will fail.

## Usage

1. **Parse resume**: Click "Choose File" (or Browse), select your resume PDF or Markdown file, then click "Parse Resume"
2. **Fetch jobs**: Enter keywords (or use config defaults) and click "Fetch Jobs"
3. **Copy profile**: Use the Copy buttons to paste name, email, skills into application forms

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs` | GET | Fetch jobs (query: `keywords`, `location`, `min_score`) |
| `/api/upload-resume` | POST | Upload and parse resume (multipart form: `file`) |
| `/api/profile` | GET | Get cached profile |
| `/api/profile/answers` | GET | Get profile formatted for copy-paste |

## Project Structure

```
job-app-assistant/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── services/      # Job fetch, resume parse, matching
│   │   ├── models/        # Pydantic schemas
│   │   └── config.py
│   ├── main.py
│   └── requirements.txt   (use root requirements.txt)
├── config/
│   └── user_config.example.yaml
├── frontend/
│   └── index.html         # Simple dashboard
├── .env.example
├── requirements.txt
└── README.md
```

## Why No LinkedIn/Indeed?

Scraping LinkedIn and Indeed violates their Terms of Service and can result in account bans. This app uses only official APIs (Adzuna, Greenhouse, Lever) to stay compliant.

## License

MIT
