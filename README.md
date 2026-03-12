# Career Crox CRM - Supabase Ready Package

This package removes Google Sheets and Google Drive dependencies from the application workflow and uses a database-driven setup.

## Stack
- Flask
- Supabase Postgres via `DATABASE_URL`
- Render deployment
- HTML/CSS/JavaScript frontend

## What changed
- Google sample sheet dependency removed from the app flow
- Database layer updated to support Supabase Postgres through `DATABASE_URL`
- SQLite fallback kept for local testing only
- Login, candidate creation, task creation, JD creation, interview creation, notes, notifications, and chat remain functional
- Interface text standardized to professional English
- Added 10 new light scenic and glass-style themes without removing the existing themes

## Local run
```bash
pip install -r requirements.txt
python app.py
```

## Render deployment
Build command:
```bash
pip install -r requirements.txt
```

Start command:
```bash
gunicorn app:app
```

## Environment variables
- `SECRET_KEY`
- `DATABASE_URL`

## Sample logins
All sample accounts use password `demo123`.
- manager1
- tlnorth
- tleast
- rec1
- rec2
- rec3
- rec4
