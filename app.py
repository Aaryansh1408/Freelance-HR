
import os
import random
import sqlite3

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "career_crox_demo.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = os.environ.get("SECRET_KEY", "career-crox-demo-secret-key")

SIDEBAR_ITEMS = [
    ("Dashboard", "dashboard", {}),
    ("Candidates", "candidates", {}),
    ("JD Centre", "jds", {}),
    ("Interviews", "interviews", {}),
    ("Tasks", "tasks", {}),
    ("Dialer", "module_page", {"slug": "dialer"}),
    ("Meeting Room", "module_page", {"slug": "meeting-room"}),
    ("Learning Hub", "module_page", {"slug": "learning-hub"}),
    ("Social Career Crox", "module_page", {"slug": "social-career-crox"}),
    ("Wallet & Rewards", "module_page", {"slug": "wallet-rewards"}),
    ("Payout Tracker", "module_page", {"slug": "payout-tracker"}),
    ("Reports", "module_page", {"slug": "reports"}),
    ("Admin Control", "admin_page", {}),
    ("Mega Blueprint", "blueprint_page", {}),
]

MODULE_SUMMARIES = {
    "dialer": {
        "title": "Dialer Command Center",
        "summary": "Call outcomes, talktime, callback suggestions, and recruiter productivity in one place.",
        "cards": [("Connected Today", "64"), ("Callbacks Due", "18"), ("Talktime", "06h 42m"), ("Best Hour", "10-11 AM")],
        "items": ["One-click dial flow", "Call outcome popup", "Hourly scoreboard", "Talktime analytics", "Follow-up suggestion engine"]
    },
    "meeting-room": {
        "title": "Meeting Room",
        "summary": "Create, join, and monitor internal meetings with attendance and quick notes.",
        "cards": [("Meetings Today", "7"), ("Live Rooms", "2"), ("Attendance Rate", "91%"), ("Pending Minutes", "3")],
        "items": ["Create Meeting", "Join Meeting", "Attendance", "Raise Hand", "Meeting chat"]
    },
    "learning-hub": {
        "title": "Learning Hub",
        "summary": "Training videos, process notes, and coaching clips for recruiters and TLs.",
        "cards": [("Videos", "24"), ("Playlists", "6"), ("Completion", "72%"), ("New This Week", "4")],
        "items": ["Airtel process videos", "Interview objection handling", "Salary negotiation tips", "Manager coaching clips"]
    },
    "social-career-crox": {
        "title": "Social Career Crox",
        "summary": "Plan social posts, manage queue, and track posting status across platforms.",
        "cards": [("Queued Posts", "12"), ("Posted", "41"), ("Missed", "2"), ("This Week Reach", "8.2k")],
        "items": ["Schedule Post", "Post Queue", "Posted Posts", "Missed Posts", "Platform filters"]
    },
    "wallet-rewards": {
        "title": "Wallet & Rewards",
        "summary": "Trips, reward milestones, and streak-based motivation without the fake motivational posters.",
        "cards": [("Reward Budget", "₹42,000"), ("Eligible Recruiters", "6"), ("Nearest Milestone", "2 joinings"), ("Trips Active", "3")],
        "items": ["20 Joining → Goa Trip", "10 Interview Conversions → Bonus", "Monthly target streak", "Reward history"]
    },
    "payout-tracker": {
        "title": "Payout Tracker",
        "summary": "Eligibility, confirmations, invoice readiness, and team-wise payout visibility.",
        "cards": [("Eligible Profiles", "11"), ("Client Confirmations", "8"), ("Invoice Ready", "6"), ("Pending Cases", "5")],
        "items": ["Recruiter earning view", "Team earnings", "Target vs achieved", "60-day eligible tracker", "Dispute notes"]
    },
    "reports": {
        "title": "Reports",
        "summary": "Funnel, conversion, source, and location reports for managers who enjoy charts more than chaos.",
        "cards": [("Lead → Join", "8.6%"), ("Top Source", "Naukri"), ("Top City", "Noida"), ("Top Recruiter", "Ritika")],
        "items": ["Daily report", "Weekly funnel", "Source performance", "Location analytics", "Recruiter efficiency"]
    }
}

SAMPLE_USERS = [
    ("manager1", "Aman Verma", "Operations Manager", "manager", "HQ", "", "demo123"),
    ("tlnorth", "Neha Singh", "Team Lead - North", "tl", "North", "manager1", "demo123"),
    ("tleast", "Pooja Das", "Team Lead - East", "tl", "East", "manager1", "demo123"),
    ("rec1", "Ritika Sharma", "Recruiter", "recruiter", "North", "tlnorth", "demo123"),
    ("rec2", "Mohit Yadav", "Recruiter", "recruiter", "North", "tlnorth", "demo123"),
    ("rec3", "Barnali Roy", "Recruiter", "recruiter", "East", "tleast", "demo123"),
    ("rec4", "Meenakshi S A", "Recruiter", "recruiter", "East", "tleast", "demo123"),
]

SAMPLE_JDS = [
    ("JD-101", "Airtel Inbound Support", "Noida", "0-2 yrs", 12000, 60, "Open"),
    ("JD-102", "Tech Sales Executive", "Gurugram", "1-3 yrs", 18000, 45, "Open"),
    ("JD-103", "HR Recruiter", "Remote", "0-1 yrs", 9000, 30, "Hot"),
    ("JD-104", "Customer Success Associate", "Bangalore", "1-2 yrs", 15000, 60, "Open"),
    ("JD-105", "Telecaller Premium", "Delhi", "0-2 yrs", 11000, 45, "Paused"),
    ("JD-106", "Collections Support", "Lucknow", "1-3 yrs", 14000, 60, "Open"),
    ("JD-107", "Field Sales Coordinator", "Kanpur", "1-4 yrs", 20000, 90, "Hot"),
    ("JD-108", "Insurance Backend", "Jaipur", "0-2 yrs", 10000, 45, "Open"),
    ("JD-109", "Operations Analyst", "Pune", "2-4 yrs", 22000, 90, "Open"),
    ("JD-110", "Retail Hiring Specialist", "Indore", "1-3 yrs", 13000, 60, "Open"),
]

SAMPLE_CANDIDATES = [
    ("CAND-001", "Sankalp Raj", "8112976914", "Lucknow", "1.5 years", "Interview", "rec1", "tlnorth", "JD-101", "Bachelor's"),
    ("CAND-002", "Aditi Chauhan", "9876543210", "Noida", "2 years", "Screening", "rec1", "tlnorth", "JD-102", "Bachelor's"),
    ("CAND-003", "Rohit Kumar", "9123456780", "Kanpur", "0.8 years", "Applied", "rec2", "tlnorth", "JD-103", "Higher Secondary"),
    ("CAND-004", "Anjali Gupta", "9988776655", "Delhi", "3 years", "Selected", "rec2", "tlnorth", "JD-104", "Master's"),
    ("CAND-005", "Satyam Dev", "8102973967", "Kolkata", "1 year", "Follow-up", "rec3", "tleast", "JD-108", "Bachelor's"),
    ("CAND-006", "Priya Nair", "9090909090", "Bangalore", "2.5 years", "Interview", "rec3", "tleast", "JD-104", "Bachelor's"),
    ("CAND-007", "Kanani Nirva", "7984586724", "Vadodara", "1.2 years", "Rejected", "rec4", "tleast", "JD-110", "Bachelor's"),
    ("CAND-008", "Shrusti Kanadam", "9449691279", "Bangalore", "0.5 years", "Applied", "rec4", "tleast", "JD-103", "Higher Secondary"),
    ("CAND-009", "Pooja Singh", "9899583818", "Faridabad", "2.1 years", "Joined", "rec1", "tlnorth", "JD-101", "Bachelor's"),
    ("CAND-010", "Aviraj Chakraborty", "7044410868", "Kolkata", "1.8 years", "Screening", "rec3", "tleast", "JD-106", "Bachelor's"),
]

SAMPLE_SUBMISSIONS = [
    ("CAND-001", "JD-101", "rec1", "Submitted", -7),
    ("CAND-002", "JD-102", "rec1", "Shortlisted", -4),
    ("CAND-003", "JD-103", "rec2", "Submitted", -2),
    ("CAND-004", "JD-104", "rec2", "Selected", -10),
    ("CAND-005", "JD-108", "rec3", "Interview", -3),
    ("CAND-006", "JD-104", "rec3", "Interview", -1),
    ("CAND-007", "JD-110", "rec4", "Rejected", -8),
    ("CAND-008", "JD-103", "rec4", "Submitted", -1),
    ("CAND-009", "JD-101", "rec1", "Joined", -20),
    ("CAND-010", "JD-106", "rec3", "Screening", -2),
]

SAMPLE_INTERVIEWS = [
    ("CAND-001", "JD-101", "Screening", 1, "Scheduled"),
    ("CAND-002", "JD-102", "Shortlisted", 2, "Confirmed"),
    ("CAND-003", "JD-103", "Screening", 0, "Pending"),
    ("CAND-004", "JD-104", "Selected", -1, "Completed"),
    ("CAND-005", "JD-108", "Shortlisted", 1, "Confirmed"),
    ("CAND-006", "JD-104", "Screening", 0, "Scheduled"),
    ("CAND-007", "JD-110", "Rejected", -2, "Closed"),
    ("CAND-008", "JD-103", "Applied", 3, "Scheduled"),
    ("CAND-009", "JD-101", "Selected", -10, "Completed"),
    ("CAND-010", "JD-106", "Screening", 1, "Scheduled"),
]

SAMPLE_TASKS = [
    ("Send JD to Sankalp Raj", "Share latest JD and collect updated CV", "rec1", "High", "Open", 0),
    ("Follow up Aditi", "Call back for final salary expectation", "rec1", "Medium", "Pending", 1),
    ("Interview prep Rohit", "Guide candidate for recruiter round", "rec2", "High", "Open", 0),
    ("Collect docs Anjali", "Need PAN and bank details", "rec2", "Medium", "Closed", -1),
    ("Check no-show trend", "Review east team reschedules", "tleast", "High", "Open", 2),
    ("Call Satyam Dev", "Candidate requested callback", "rec3", "High", "Pending", 0),
    ("Schedule Priya panel", "Align with manager availability", "rec3", "Medium", "Open", 1),
    ("Share rejection feedback", "Close loop for Kanani", "rec4", "Low", "Closed", -2),
    ("Welcome joined candidate", "Add to joined tracker", "tlnorth", "Low", "Closed", -3),
    ("Review daily funnel", "Prepare team report", "manager1", "High", "Open", 0),
]

SAMPLE_PUBLIC_NOTES = [
    ("CAND-001", "rec1", "public", "Candidate confirmed he is currently active and can attend interview tomorrow at 11 AM.", -3),
    ("CAND-001", "tlnorth", "public", "Salary expectation looks within range. Need final confirmation on shift comfort.", -2),
    ("CAND-001", "rec1", "public", "Shared JD on WhatsApp and candidate acknowledged.", -1),
    ("CAND-001", "manager1", "public", "Keep this profile warm. Good chance of closure if call is handled properly.", -1),
    ("CAND-001", "rec1", "public", "Candidate asked if joining location can be discussed after HR round.", -1),
    ("CAND-001", "tlnorth", "public", "Feedback reviewed. Proceed with interview confirmation.", 0),
    ("CAND-002", "rec1", "public", "Candidate wants ₹24k in-hand; try to align with current budget.", -2),
    ("CAND-004", "rec2", "public", "Selected and awaiting joining date confirmation.", -4),
    ("CAND-006", "rec3", "public", "Candidate attended screening well, manager feedback positive.", -1),
    ("CAND-009", "manager1", "public", "60-day payout watch started for this joined profile.", -5),
]

SAMPLE_PRIVATE_NOTES = [
    ("CAND-001", "rec1", "private", "Personal note: candidate responds faster after 6 PM. Don't spam in daytime.", -2),
    ("CAND-001", "manager1", "private", "Manager note: likely good retention profile if handled patiently.", -1),
    ("CAND-002", "rec1", "private", "Seems negotiable. Might accept lower fixed if incentives are clear.", -1),
    ("CAND-003", "rec2", "private", "Candidate sounded confused about role. Need simpler explanation.", 0),
    ("CAND-004", "rec2", "private", "Strong profile. Can be used as benchmark for same JD.", -3),
    ("CAND-005", "rec3", "private", "Noisy background during calls. Better to schedule evening callback.", -1),
    ("CAND-006", "manager1", "private", "Manager note: keep TL informed if this becomes high-priority.", 0),
    ("CAND-007", "rec4", "private", "Low interest level. Avoid too much time investment.", -4),
    ("CAND-009", "manager1", "private", "Joined case useful for payout demonstration.", -8),
    ("CAND-010", "rec3", "private", "Maybe better suited for JD-103 than JD-106.", -1),
]

SAMPLE_MESSAGES = [
    ("manager1", "tlnorth", "Please review all new public notes on Sankalp today.", -1),
    ("tlnorth", "rec1", "Seen. Push for confirmation and update the note history.", -1),
    ("rec1", "tlnorth", "Done. Candidate is responsive now.", 0),
    ("tleast", "rec3", "Need east team interview tracker by evening.", 0),
    ("rec3", "tleast", "Working on it. Priya and Satyam are updated.", 0),
    ("manager1", "rec4", "Please clean rejection reasons in your pipeline.", -2),
    ("rec4", "manager1", "Doing it today.", -2),
    ("rec2", "tlnorth", "Anjali selected. Docs pending only.", -3),
    ("manager1", "rec2", "Good. Add note and move to joined watch.", -3),
    ("rec3", "manager1", "Need approval for interview reschedule trend review.", -1),
]

def _postgres_connect():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def _adapt_query(query: str) -> str:
    if not USE_POSTGRES:
        return query
    return query.replace('?', '%s').replace('datetime(', '(')


def _row_value(row, key, default=None):
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return default


def get_db():
    if "db" not in g:
        if USE_POSTGRES:
            g.db = _postgres_connect()
        else:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db


def query_db(query, params=(), one=False):
    db = get_db()
    cur = db.cursor()
    cur.execute(_adapt_query(query), params)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, params=()):
    db = get_db()
    cur = db.cursor()
    sql = _adapt_query(query)
    is_insert = query.lstrip().upper().startswith("INSERT")
    if USE_POSTGRES and is_insert and "RETURNING" not in query.upper():
        sql += " RETURNING id"
    cur.execute(sql, params)
    lastrowid = None
    if USE_POSTGRES and is_insert:
        row = cur.fetchone()
        lastrowid = _row_value(row, "id")
    else:
        lastrowid = getattr(cur, 'lastrowid', None)
    db.commit()
    cur.close()
    return lastrowid


def init_db():
    if USE_POSTGRES:
        db = _postgres_connect()
        cur = db.cursor()
        statements = [
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE,
                full_name TEXT,
                designation TEXT,
                role TEXT,
                team TEXT,
                manager_username TEXT,
                password TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS jds (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE,
                title TEXT,
                location TEXT,
                experience_required TEXT,
                payout INTEGER,
                payout_days INTEGER,
                status TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS candidates (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE,
                full_name TEXT,
                phone TEXT,
                location TEXT,
                experience TEXT,
                status TEXT,
                recruiter_username TEXT,
                tl_username TEXT,
                jd_code TEXT,
                qualification TEXT,
                created_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS submissions (
                id SERIAL PRIMARY KEY,
                candidate_code TEXT,
                jd_code TEXT,
                recruiter_username TEXT,
                status TEXT,
                submitted_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS interviews (
                id SERIAL PRIMARY KEY,
                candidate_code TEXT,
                jd_code TEXT,
                stage TEXT,
                scheduled_at TEXT,
                status TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT,
                description TEXT,
                assigned_to TEXT,
                priority TEXT,
                status TEXT,
                due_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                candidate_code TEXT,
                username TEXT,
                note_type TEXT,
                body TEXT,
                created_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                username TEXT,
                candidate_code TEXT,
                title TEXT,
                message TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                sender_username TEXT,
                recipient_username TEXT,
                body TEXT,
                created_at TEXT
            )""",
        ]
        for stmt in statements:
            cur.execute(stmt)
        db.commit()
        cur.close()
        db.close()
        return

    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        full_name TEXT,
        designation TEXT,
        role TEXT,
        team TEXT,
        manager_username TEXT,
        password TEXT
    );

    CREATE TABLE IF NOT EXISTS jds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        title TEXT,
        location TEXT,
        experience_required TEXT,
        payout INTEGER,
        payout_days INTEGER,
        status TEXT
    );

    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        full_name TEXT,
        phone TEXT,
        location TEXT,
        experience TEXT,
        status TEXT,
        recruiter_username TEXT,
        tl_username TEXT,
        jd_code TEXT,
        qualification TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_code TEXT,
        jd_code TEXT,
        recruiter_username TEXT,
        status TEXT,
        submitted_at TEXT
    );

    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_code TEXT,
        jd_code TEXT,
        stage TEXT,
        scheduled_at TEXT,
        status TEXT
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        assigned_to TEXT,
        priority TEXT,
        status TEXT,
        due_at TEXT
    );

    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_code TEXT,
        username TEXT,
        note_type TEXT,
        body TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        candidate_code TEXT,
        title TEXT,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_username TEXT,
        recipient_username TEXT,
        body TEXT,
        created_at TEXT
    );
    """)
    db.commit()
    db.close()


def seed_demo_data():
    if USE_POSTGRES:
        db = _postgres_connect()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM users")
        existing = cur.fetchone()["c"]
        if existing > 0:
            cur.close()
            db.close()
            return

        for row in SAMPLE_USERS:
            cur.execute("""INSERT INTO users (username, full_name, designation, role, team, manager_username, password)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""", row)
        for row in SAMPLE_JDS:
            cur.execute("""INSERT INTO jds (code, title, location, experience_required, payout, payout_days, status)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""", row)

        now = datetime.now()
        for row in SAMPLE_CANDIDATES:
            created_at = (now - timedelta(days=random.randint(1, 15), hours=random.randint(0, 18))).strftime("%Y-%m-%d %H:%M")
            cur.execute("""INSERT INTO candidates
                (code, full_name, phone, location, experience, status, recruiter_username, tl_username, jd_code, qualification, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", row + (created_at,))

        for candidate_code, jd_code, recruiter, status, offset_days in SAMPLE_SUBMISSIONS:
            submitted_at = (now + timedelta(days=offset_days)).strftime("%Y-%m-%d %H:%M")
            cur.execute("""INSERT INTO submissions (candidate_code, jd_code, recruiter_username, status, submitted_at)
                           VALUES (%s, %s, %s, %s, %s)""", (candidate_code, jd_code, recruiter, status, submitted_at))

        for candidate_code, jd_code, stage, day_offset, status in SAMPLE_INTERVIEWS:
            scheduled_at = (now + timedelta(days=day_offset, hours=random.randint(9, 17))).strftime("%Y-%m-%d %H:%M")
            cur.execute("""INSERT INTO interviews (candidate_code, jd_code, stage, scheduled_at, status)
                           VALUES (%s, %s, %s, %s, %s)""", (candidate_code, jd_code, stage, scheduled_at, status))

        for title, desc, assigned, priority, status, day_offset in SAMPLE_TASKS:
            due_at = (now + timedelta(days=day_offset, hours=random.randint(8, 18))).strftime("%Y-%m-%d %H:%M")
            cur.execute("""INSERT INTO tasks (title, description, assigned_to, priority, status, due_at)
                           VALUES (%s, %s, %s, %s, %s, %s)""", (title, desc, assigned, priority, status, due_at))

        for candidate_code, username, note_type, body, day_offset in SAMPLE_PUBLIC_NOTES + SAMPLE_PRIVATE_NOTES:
            created_at = (now + timedelta(days=day_offset, hours=random.randint(8, 20), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M")
            cur.execute("""INSERT INTO notes (candidate_code, username, note_type, body, created_at)
                           VALUES (%s, %s, %s, %s, %s)""", (candidate_code, username, note_type, body, created_at))

        for username, candidate_code, title, message, is_read, day_offset in SAMPLE_NOTIFICATIONS:
            created_at = (now + timedelta(days=day_offset, hours=random.randint(7, 22), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M")
            cur.execute("""INSERT INTO notifications (username, candidate_code, title, message, is_read, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s)""", (username, candidate_code, title, message, is_read, created_at))

        for sender, recipient, body, day_offset in SAMPLE_MESSAGES:
            created_at = (now + timedelta(days=day_offset, hours=random.randint(8, 21), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M")
            cur.execute("""INSERT INTO messages (sender_username, recipient_username, body, created_at)
                           VALUES (%s, %s, %s, %s)""", (sender, recipient, body, created_at))

        db.commit()
        cur.close()
        db.close()
        return

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    existing = cur.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    if existing > 0:
        db.close()
        return

    for row in SAMPLE_USERS:
        cur.execute("""INSERT INTO users (username, full_name, designation, role, team, manager_username, password)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""", row)

    for row in SAMPLE_JDS:
        cur.execute("""INSERT INTO jds (code, title, location, experience_required, payout, payout_days, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""", row)

    now = datetime.now()
    for row in SAMPLE_CANDIDATES:
        created_at = (now - timedelta(days=random.randint(1, 15), hours=random.randint(0, 18))).strftime("%Y-%m-%d %H:%M")
        cur.execute("""INSERT INTO candidates
            (code, full_name, phone, location, experience, status, recruiter_username, tl_username, jd_code, qualification, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", row + (created_at,))

    for candidate_code, jd_code, recruiter, status, offset_days in SAMPLE_SUBMISSIONS:
        submitted_at = (now + timedelta(days=offset_days)).strftime("%Y-%m-%d %H:%M")
        cur.execute("""INSERT INTO submissions (candidate_code, jd_code, recruiter_username, status, submitted_at)
                       VALUES (?, ?, ?, ?, ?)""", (candidate_code, jd_code, recruiter, status, submitted_at))

    for candidate_code, jd_code, stage, day_offset, status in SAMPLE_INTERVIEWS:
        scheduled_at = (now + timedelta(days=day_offset, hours=random.randint(9, 17))).strftime("%Y-%m-%d %H:%M")
        cur.execute("""INSERT INTO interviews (candidate_code, jd_code, stage, scheduled_at, status)
                       VALUES (?, ?, ?, ?, ?)""", (candidate_code, jd_code, stage, scheduled_at, status))

    for title, desc, assigned, priority, status, day_offset in SAMPLE_TASKS:
        due_at = (now + timedelta(days=day_offset, hours=random.randint(8, 18))).strftime("%Y-%m-%d %H:%M")
        cur.execute("""INSERT INTO tasks (title, description, assigned_to, priority, status, due_at)
                       VALUES (?, ?, ?, ?, ?, ?)""", (title, desc, assigned, priority, status, due_at))

    for candidate_code, username, note_type, body, day_offset in SAMPLE_PUBLIC_NOTES + SAMPLE_PRIVATE_NOTES:
        created_at = (now + timedelta(days=day_offset, hours=random.randint(8, 20), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M")
        cur.execute("""INSERT INTO notes (candidate_code, username, note_type, body, created_at)
                       VALUES (?, ?, ?, ?, ?)""", (candidate_code, username, note_type, body, created_at))

    for username, candidate_code, title, message, is_read, day_offset in SAMPLE_NOTIFICATIONS:
        created_at = (now + timedelta(days=day_offset, hours=random.randint(7, 22), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M")
        cur.execute("""INSERT INTO notifications (username, candidate_code, title, message, is_read, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""", (username, candidate_code, title, message, is_read, created_at))

    for sender, recipient, body, day_offset in SAMPLE_MESSAGES:
        created_at = (now + timedelta(days=day_offset, hours=random.randint(8, 21), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M")
        cur.execute("""INSERT INTO messages (sender_username, recipient_username, body, created_at)
                       VALUES (?, ?, ?, ?)""", (sender, recipient, body, created_at))

    db.commit()
    db.close()


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.context_processor
def inject_globals():
    user = current_user()
    unread = 0
    if user:
        row = query_db("SELECT COUNT(*) as c FROM notifications WHERE username = ? AND is_read = 0", (user["username"],), one=True)
        unread = row["c"] if row else 0
    return {
        "sidebar_items": SIDEBAR_ITEMS,
        "current_user_data": user,
        "unread_notifications": unread,
        "now": datetime.now(),
    }

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user["role"] != "manager":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def current_user():
    uname = session.get("impersonated_as") or session.get("username")
    if not uname:
        return None
    return query_db("SELECT * FROM users WHERE username = ?", (uname,), one=True)

def visible_private_notes(candidate_code, user):
    if user["role"] == "manager":
        return query_db("""
            SELECT n.*, u.full_name, u.designation
            FROM notes n
            JOIN users u ON u.username = n.username
            WHERE n.candidate_code = ? AND n.note_type = 'private'
            ORDER BY datetime(n.created_at) DESC
        """, (candidate_code,))
    return query_db("""
        SELECT n.*, u.full_name, u.designation
        FROM notes n
        JOIN users u ON u.username = n.username
        WHERE n.candidate_code = ? AND n.note_type = 'private' AND n.username = ?
        ORDER BY datetime(n.created_at) DESC
    """, (candidate_code, user["username"]))

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.context_processor
def inject_globals():
    user = current_user()
    unread = 0
    if user:
        row = query_db("SELECT COUNT(*) as c FROM notifications WHERE username = ? AND is_read = 0", (user["username"],), one=True)
        unread = row["c"] if row else 0
    return {
        "sidebar_items": SIDEBAR_ITEMS,
        "current_user_data": user,
        "unread_notifications": unread,
        "now": datetime.now(),
    }

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = query_db("SELECT * FROM users WHERE username = ? AND password = ?", (username, password), one=True)
        if user:
            session["username"] = user["username"]
            flash(f"Welcome back, {user['full_name']}. The dashboard was waiting, tragically.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid login. Demo credentials are on screen because chaos is optional.", "danger")
    demo_users = query_db("SELECT username, full_name, designation, role FROM users ORDER BY role, id")
    return render_template("login.html", demo_users=demo_users)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def root():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    total_profiles = query_db("SELECT COUNT(*) as c FROM candidates", one=True)["c"]
    today_calls = 52
    interviews_today = query_db("SELECT COUNT(*) as c FROM interviews WHERE date(scheduled_at) = date('now')", one=True)["c"]
    active_managers = query_db("SELECT COUNT(*) as c FROM users WHERE role IN ('manager','tl')", one=True)["c"]
    recent_activity = query_db("""
        SELECT c.full_name, c.status, c.code, c.created_at, u.full_name AS recruiter_name
        FROM candidates c
        LEFT JOIN users u ON u.username = c.recruiter_username
        ORDER BY datetime(c.created_at) DESC
        LIMIT 6
    """)
    due_tasks = query_db("""
        SELECT t.*, u.full_name
        FROM tasks t
        LEFT JOIN users u ON u.username = t.assigned_to
        ORDER BY CASE t.status WHEN 'Open' THEN 1 WHEN 'Pending' THEN 2 ELSE 3 END, datetime(t.due_at) ASC
        LIMIT 6
    """)
    manager_monitoring = query_db("""
        SELECT u.full_name, u.designation, 
               (SELECT COUNT(*) FROM candidates c WHERE c.recruiter_username = u.username) as candidate_count,
               (SELECT COUNT(*) FROM tasks t WHERE t.assigned_to = u.username AND t.status != 'Closed') as open_tasks
        FROM users u
        WHERE u.role IN ('recruiter','tl')
        ORDER BY u.role DESC, candidate_count DESC
        LIMIT 6
    """)
    unread_notes = query_db("""
        SELECT n.title, n.message, n.created_at, c.full_name
        FROM notifications n
        LEFT JOIN candidates c ON c.code = n.candidate_code
        WHERE n.username = ?
        ORDER BY datetime(n.created_at) DESC
        LIMIT 5
    """, (user["username"],))
    return render_template("dashboard.html",
        total_profiles=total_profiles,
        today_calls=today_calls,
        interviews_today=interviews_today,
        active_managers=active_managers,
        recent_activity=recent_activity,
        due_tasks=due_tasks,
        manager_monitoring=manager_monitoring,
        unread_notes=unread_notes
    )

@app.route("/candidates")
@login_required
def candidates():
    q = request.args.get("q", "").strip()
    recruiter = request.args.get("recruiter", "").strip()
    status = request.args.get("status", "").strip()
    conditions = []
    params = []
    sql = """
        SELECT c.*, r.full_name AS recruiter_name, r.username AS recruiter_code, t.full_name AS tl_name, j.title AS jd_title
        FROM candidates c
        LEFT JOIN users r ON r.username = c.recruiter_username
        LEFT JOIN users t ON t.username = c.tl_username
        LEFT JOIN jds j ON j.code = c.jd_code
    """
    if q:
        like = f"%{q}%"
        conditions.append("(c.full_name LIKE ? OR c.phone LIKE ? OR c.location LIKE ? OR c.status LIKE ? OR c.jd_code LIKE ?)")
        params.extend([like, like, like, like, like])
    if recruiter:
        conditions.append("c.recruiter_username = ?")
        params.append(recruiter)
    if status:
        conditions.append("c.status = ?")
        params.append(status)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY datetime(c.created_at) DESC"
    rows = query_db(sql, params)
    recruiters = query_db("SELECT username, full_name FROM users WHERE role='recruiter' ORDER BY full_name")
    statuses = [r['status'] for r in query_db("SELECT DISTINCT status FROM candidates ORDER BY status")]
    return render_template("candidates.html", candidates=rows, q=q, recruiters=recruiters, current_recruiter=recruiter, statuses=statuses, current_status=status)

@app.route("/candidate/<candidate_code>")
@login_required
def candidate_detail(candidate_code):
    user = current_user()
    candidate = query_db("""
        SELECT c.*, r.full_name AS recruiter_name, r.designation AS recruiter_designation,
               t.full_name AS tl_name, t.designation AS tl_designation, j.title AS jd_title, j.payout, j.status as jd_status
        FROM candidates c
        LEFT JOIN users r ON r.username = c.recruiter_username
        LEFT JOIN users t ON t.username = c.tl_username
        LEFT JOIN jds j ON j.code = c.jd_code
        WHERE c.code = ?
    """, (candidate_code,), one=True)
    if not candidate:
        abort(404)
    public_notes = query_db("""
        SELECT n.*, u.full_name, u.designation
        FROM notes n
        JOIN users u ON u.username = n.username
        WHERE n.candidate_code = ? AND n.note_type = 'public'
        ORDER BY datetime(n.created_at) DESC
    """, (candidate_code,))
    private_notes = visible_private_notes(candidate_code, user)
    related_notifications = query_db("""
        SELECT *
        FROM notifications
        WHERE username = ? AND candidate_code = ?
        ORDER BY datetime(created_at) DESC
        LIMIT 8
    """, (user["username"], candidate_code))
    timeline = query_db("""
        SELECT * FROM (
            SELECT 'Submission' AS event_type, status AS label, submitted_at AS event_time, jd_code, recruiter_username AS owner
            FROM submissions WHERE candidate_code = ?
            UNION ALL
            SELECT 'Interview' AS event_type, status AS label, scheduled_at AS event_time, jd_code, '' AS owner
            FROM interviews WHERE candidate_code = ?
        ) t
        ORDER BY datetime(event_time) DESC
    """, (candidate_code, candidate_code))
    return render_template("candidate_detail.html",
                           candidate=candidate,
                           public_notes=public_notes,
                           private_notes=private_notes,
                           related_notifications=related_notifications,
                           timeline=timeline)

@app.route("/candidate/<candidate_code>/add-note", methods=["POST"])
@login_required
def add_note(candidate_code):
    user = current_user()
    note_type = request.form.get("note_type", "public")
    body = request.form.get("body", "").strip()
    if not body:
        flash("Empty note save नहीं होगा. Software भी कुछ standards रखता है.", "danger")
        return redirect(url_for("candidate_detail", candidate_code=candidate_code))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    execute_db("""INSERT INTO notes (candidate_code, username, note_type, body, created_at)
                  VALUES (?, ?, ?, ?, ?)""", (candidate_code, user["username"], note_type, body, now_str))
    candidate = query_db("SELECT * FROM candidates WHERE code = ?", (candidate_code,), one=True)
    if note_type == "public" and candidate:
        targets = [candidate["recruiter_username"], candidate["tl_username"]]
        preview = body[:90] + ('...' if len(body) > 90 else '')
        for target in targets:
            execute_db("""INSERT INTO notifications (username, candidate_code, title, message, is_read, created_at)
                          VALUES (?, ?, ?, ?, 0, ?)""",
                       (target, candidate_code, f"Note updated: {candidate['full_name']}",
                        f"{user['full_name']} ({user['designation']}) added a public note on {candidate['full_name']}: {preview}", now_str))
    flash("Note saved successfully.", "success")
    return redirect(url_for("candidate_detail", candidate_code=candidate_code))

@app.route("/jds")
@login_required
def jds():
    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()
    sql = "SELECT * FROM jds"
    conditions=[]
    params=[]
    if status:
        conditions.append("status = ?")
        params.append(status)
    if q:
        like=f"%{q}%"
        conditions.append("(code LIKE ? OR title LIKE ? OR location LIKE ?)")
        params.extend([like, like, like])
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY payout DESC, code ASC"
    rows = query_db(sql, params)
    status_choices = [r['status'] for r in query_db("SELECT DISTINCT status FROM jds ORDER BY status")]
    return render_template("jds.html", jds=rows, status=status, status_choices=status_choices, q=q)

@app.route("/interviews")
@login_required
def interviews():
    current_stage = request.args.get("stage", "All")
    params = []
    sql = """
        SELECT i.*, c.full_name, j.title
        FROM interviews i
        LEFT JOIN candidates c ON c.code = i.candidate_code
        LEFT JOIN jds j ON j.code = i.jd_code
    """
    if current_stage and current_stage != "All":
        sql += " WHERE i.stage = ? "
        params.append(current_stage)
    sql += " ORDER BY datetime(i.scheduled_at) ASC"
    rows = query_db(sql, params)
    return render_template("interviews.html", interviews=rows, current_stage=current_stage)

@app.route("/tasks")
@login_required
def tasks():
    user = current_user()
    if user["role"] == "manager":
        rows = query_db("""
            SELECT t.*, u.full_name
            FROM tasks t
            LEFT JOIN users u ON u.username = t.assigned_to
            ORDER BY datetime(t.due_at) ASC
        """)
    else:
        rows = query_db("""
            SELECT t.*, u.full_name
            FROM tasks t
            LEFT JOIN users u ON u.username = t.assigned_to
            WHERE t.assigned_to = ? OR ? IN (SELECT manager_username FROM users WHERE username = t.assigned_to)
            ORDER BY datetime(t.due_at) ASC
        """, (user["username"], user["username"]))
    return render_template("tasks.html", tasks=rows)

@app.route("/submissions")
@login_required
def submissions():
    rows = query_db("""
        SELECT s.*, c.full_name, j.title
        FROM submissions s
        LEFT JOIN candidates c ON c.code = s.candidate_code
        LEFT JOIN jds j ON j.code = s.jd_code
        ORDER BY datetime(s.submitted_at) DESC
    """)
    return render_template("submissions.html", submissions=rows)

@app.route("/notifications")
@login_required
def notifications_page():
    user = current_user()
    rows = query_db("""
        SELECT n.*, c.full_name
        FROM notifications n
        LEFT JOIN candidates c ON c.code = n.candidate_code
        WHERE n.username = ?
        ORDER BY datetime(n.created_at) DESC
    """, (user["username"],))
    return render_template("notifications.html", notifications=rows)

@app.route("/notifications/mark-all-read")
@login_required
def mark_all_read():
    user = current_user()
    execute_db("UPDATE notifications SET is_read = 1 WHERE username = ?", (user["username"],))
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications_page"))

@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat_page():
    user = current_user()
    users = query_db("SELECT username, full_name, designation, role FROM users WHERE username != ? ORDER BY role, full_name", (user["username"],))
    selected = request.args.get("with") or (users[0]["username"] if users else None)
    if request.method == "POST":
        recipient = request.form.get("recipient")
        body = request.form.get("body", "").strip()
        if recipient and body:
            execute_db("""INSERT INTO messages (sender_username, recipient_username, body, created_at)
                          VALUES (?, ?, ?, ?)""", (user["username"], recipient, body, datetime.now().strftime("%Y-%m-%d %H:%M")))
            flash("Message sent.", "success")
            return redirect(url_for("chat_page", **{"with": recipient}))
    convo = []
    if selected:
        convo = query_db("""
            SELECT m.*, su.full_name AS sender_name, ru.full_name AS recipient_name
            FROM messages m
            LEFT JOIN users su ON su.username = m.sender_username
            LEFT JOIN users ru ON ru.username = m.recipient_username
            WHERE (m.sender_username = ? AND m.recipient_username = ?)
               OR (m.sender_username = ? AND m.recipient_username = ?)
            ORDER BY datetime(m.created_at) ASC
        """, (user["username"], selected, selected, user["username"]))
    return render_template("chat.html", users=users, selected=selected, convo=convo)

@app.route("/admin")
@login_required
@manager_required
def admin_page():
    users = query_db("SELECT * FROM users ORDER BY role, team, full_name")
    notes_count = query_db("""
        SELECT u.full_name, 
               SUM(CASE WHEN n.note_type='public' THEN 1 ELSE 0 END) as public_count,
               SUM(CASE WHEN n.note_type='private' THEN 1 ELSE 0 END) as private_count
        FROM users u
        LEFT JOIN notes n ON n.username = u.username
        GROUP BY u.username
        ORDER BY u.role, u.full_name
    """)
    return render_template("admin.html", users=users, notes_count=notes_count)


@app.route("/admin/impersonate", methods=["POST"])
@login_required
@manager_required
def impersonate_login():
    username = request.form.get("username", "").strip()
    target = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
    manager = query_db("SELECT * FROM users WHERE username = ?", (session.get("username"),), one=True)
    if not target or not manager:
        flash("Target account not found.", "danger")
        return redirect(url_for("admin_page"))
    session["impersonator"] = manager["username"]
    session["impersonated_as"] = target["username"]
    flash(f"Now viewing as {target['full_name']}.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/stop-impersonation")
@login_required
def stop_impersonation():
    if session.get("impersonator"):
        original = session.get("impersonator")
        session.pop("impersonated_as", None)
        session.pop("impersonator", None)
        session["username"] = original
        flash("Returned to manager account.", "success")
    return redirect(url_for("admin_page"))

@app.route("/module/<slug>")
@login_required
def module_page(slug):
    module = MODULE_SUMMARIES.get(slug)
    if not module:
        abort(404)
    dialer_candidates = []
    meeting_feed = []
    if slug == 'dialer':
        dialer_candidates = query_db("""
            SELECT c.code, c.full_name, c.phone, c.status, c.location, c.experience,
                   r.full_name AS recruiter_name, t.full_name AS tl_name
            FROM candidates c
            LEFT JOIN users r ON r.username = c.recruiter_username
            LEFT JOIN users t ON t.username = c.tl_username
            ORDER BY datetime(c.created_at) DESC
        """)
    if slug == 'meeting-room':
        meeting_feed = [
            {"name": "Ritika joined", "time": "03:00 PM", "state": "Joined"},
            {"name": "Mohit joined", "time": "03:02 PM", "state": "Joined"},
            {"name": "Barnali left", "time": "03:11 PM", "state": "Left"},
            {"name": "Neha joined", "time": "03:14 PM", "state": "Joined"},
        ]
    return render_template("module_page.html", module=module, slug=slug, dialer_candidates=dialer_candidates, meeting_feed=meeting_feed)

@app.route("/blueprint")
@login_required
def blueprint_page():
    blueprint_path = os.path.join(BASE_DIR, "docs", "MEGA_BLUEPRINT_120_PLUS_FEATURES.md")
    context_path = os.path.join(BASE_DIR, "docs", "CROSS_CHAT_MASTER_CONTEXT.txt")
    with open(blueprint_path, "r", encoding="utf-8") as f:
        blueprint_text = f.read()
    with open(context_path, "r", encoding="utf-8") as f:
        context_text = f.read()
    return render_template("blueprint.html", blueprint_text=blueprint_text, context_text=context_text)

@app.route("/preview")
def preview_page():
    demo_users = query_db("SELECT username, full_name, designation, role FROM users ORDER BY role, id")
    return render_template("preview.html", demo_users=demo_users)

if __name__ == "__main__":
    init_db()
    seed_demo_data()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

init_db()
seed_demo_data()
