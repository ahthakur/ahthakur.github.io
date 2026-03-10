# Job Application Assistant – Backlog

Features discussed but not yet implemented.

## Phase 2 Enhancements

### Browser Extension
- Form pre-fill: inject saved profile (name, email, LinkedIn, skills) into Greenhouse/Lever application forms when user is on an apply page
- Detect common fields and auto-populate from cached profile

### Scheduled Job Fetching
- Cron/scheduled job runs to fetch new matches periodically
- Email digest of new jobs (requires email config)
- Optional: configurable schedule (daily, weekly)

### Application Tracking
- Manual "Applied" button per job listing
- Track which jobs have been applied to
- Follow-up reminders (e.g., 1 week after application)
- Store applied jobs (SQLite or JSON)

### Deployment
- Deploy backend to Railway, Render, or similar
- Host frontend on GitHub Pages or Vercel
- Production config (env vars, CORS)

## Multi-User / Generic Version

- User authentication (sign up, login)
- Per-user config: resume URL, keywords, skills
- Point to own resume on GitHub (resume URL parsing)
- Each user gets their own profile cache and job history

## Profile & Application Helpers

### Profile Answer Library
- User-defined answers for common questions (e.g., "Why this company?", "Salary expectation?", "Availability?")
- Store in config or DB
- Endpoint to return answers for copy-paste
- Browser extension could inject these into form fields

### Cover Letter Generator
- Generate a draft cover letter from job title + company + skills
- User edits before use
- Template with placeholders

## Resume Parsing

### Resume from URL
- Parse resume from GitHub raw URL (without file upload)
- Improve reliability when network/firewall blocks outbound requests
- Fallback options when URL fetch fails

## Job Search

### Filters
- Optional toggle: "Hide low-relevance jobs" (e.g., score < 20)
- Filter by source (Adzuna only, Greenhouse only, etc.)
- Date range filter (posted in last 7 days, etc.)
