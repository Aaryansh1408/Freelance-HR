# Supabase and Render Setup

## 1. Create a new Supabase project
Create a fresh project in Supabase and wait until the database is ready.

## 2. Copy the Postgres connection string
Open Project Settings > Database > Connection string.
Use the Postgres connection string or pooler string. Paste it into `DATABASE_URL` on Render.

## 3. Add Render environment variables
- `SECRET_KEY`
- `DATABASE_URL`

## 4. Deploy
Push the files to GitHub, create a new Render Web Service, and use:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

## 5. Verify data storage
After login, add a candidate, task, JD, or interview.
Then check these tables in Supabase:
- `candidates`
- `tasks`
- `jds`
- `interviews`
- `notes`
- `messages`
- `notifications`
