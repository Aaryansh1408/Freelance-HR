
import os
import random
import re
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None
    RealDictCursor = None

from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "career_crox_local.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith("postgres")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = os.environ.get("SECRET_KEY", "career-crox-secure-key")

SIDEBAR_ITEMS = [
    ("Dashboard", "dashboard", {}),
    ("Candidates", "candidates", {}),
    ("JD Center", "jds", {}),
    ("Interviews", "interviews", {}),
    ("Tasks", "tasks", {}),
    ("Dialer", "module_page", {"slug": "dialer"}),
    ("Meeting Room", "module_page", {"slug": "meeting-room"}),
    ("Learning Hub", "module_page", {"slug": "learning-hub"}),
    ("Social Hub", "module_page", {"slug": "social-career-crox"}),
    ("Rewards", "module_page", {"slug": "wallet-rewards"}),
    ("Payout Tracker", "module_page", {"slug": "payout-tracker"}),
    ("Reports", "module_page", {"slug": "reports"}),
    ("Admin Control", "admin_page", {}),
    ("Blueprint", "blueprint_page", {}),
]

MODULE_SUMMARIES = {
    "dialer": {
        "title": "Dialer Command Center",
        "summary": "Call outcomes, talk time, callback suggestions, and recruiter productivity in one place.",
        "cards": [("Connected Today", "64"), ("Callbacks Due", "18"), ("Talk Time", "06h 42m"), ("Best Hour", "10-11 AM")],
        "items": ["One-click dial flow", "Call outcome capture", "Hourly scoreboard", "Talk time analytics", "Follow-up suggestions"]
    },
    "meeting-room": {
        "title": "Meeting Room",
        "summary": "Create, join, and monitor internal meetings with attendance and quick notes.",
        "cards": [("Meetings Today", "7"), ("Live Rooms", "2"), ("Attendance Rate", "91%"), ("Pending Minutes", "3")],
        "items": ["Create Meeting", "Join Meeting", "Attendance", "Raise Hand", "Meeting Chat"]
    },
    "learning-hub": {
        "title": "Learning Hub",
        "summary": "Training videos, process notes, and coaching resources for recruiters and team leads.",
        "cards": [("Videos", "24"), ("Playlists", "6"), ("Completion", "72%"), ("New This Week", "4")],
        "items": ["Process videos", "Interview guidance", "Salary negotiation tips", "Manager coaching resources"]
    },
    "social-career-crox": {
        "title": "Social Hub",
        "summary": "Plan social posts, manage queues, and track publishing status across platforms.",
        "cards": [("Queued Posts", "12"), ("Published", "41"), ("Missed", "2"), ("Weekly Reach", "8.2k")],
        "items": ["Schedule Post", "Post Queue", "Published Posts", "Missed Posts", "Platform Filters"]
    },
    "wallet-rewards": {
        "title": "Rewards",
        "summary": "Track reward milestones, incentive programs, and performance-based recognition.",
        "cards": [("Reward Budget", "₹42,000"), ("Eligible Recruiters", "6"), ("Nearest Milestone", "2 joinings"), ("Active Programs", "3")],
        "items": ["Performance rewards", "Interview conversion bonus", "Monthly streaks", "Reward history"]
    },
    "payout-tracker": {
        "title": "Payout Tracker",
        "summary": "Track eligibility, confirmations, invoice readiness, and team-wise payout status.",
        "cards": [("Eligible Profiles", "11"), ("Client Confirmations", "8"), ("Invoice Ready", "6"), ("Pending Cases", "5")],
        "items": ["Recruiter earnings", "Team earnings", "Target versus achieved", "60-day eligibility tracker", "Dispute notes"]
    },
    "reports": {
        "title": "Reports",
        "summary": "Review funnel, conversion, source, and location metrics from a single reporting layer.",
        "cards": [("Lead to Join", "8.6%"), ("Top Source", "Naukri"), ("Top City", "Noida"), ("Top Recruiter", "Ritika")],
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
    ("JD-103", "HR Recruiter", "Remote", "0-1 yrs", 9000, 30, "Open"),
    ("JD-104", "Customer Success Associate", "Bangalore", "1-2 yrs", 15000, 60, "Open"),
    ("JD-105", "Telecaller Premium", "Delhi", "0-2 yrs", 11000, 45, "Paused"),
    ("JD-106", "Collections Support", "Lucknow", "1-3 yrs", 14000, 60, "Open"),
    ("JD-107", "Field Sales Coordinator", "Kanpur", "1-4 yrs", 20000, 90, "Open"),
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

SAMPLE_SUBMISSIONS = [("CAND-001", "JD-101", "rec1", "Submitted", -7),("CAND-002", "JD-102", "rec1", "Shortlisted", -4),("CAND-003", "JD-103", "rec2", "Submitted", -2),("CAND-004", "JD-104", "rec2", "Selected", -10),("CAND-005", "JD-108", "rec3", "Interview", -3),("CAND-006", "JD-104", "rec3", "Interview", -1),("CAND-007", "JD-110", "rec4", "Rejected", -8),("CAND-008", "JD-103", "rec4", "Submitted", -1),("CAND-009", "JD-101", "rec1", "Joined", -20),("CAND-010", "JD-106", "rec3", "Screening", -2)]
SAMPLE_INTERVIEWS = [("CAND-001", "JD-101", "Screening", 1, "Scheduled"),("CAND-002", "JD-102", "Shortlisted", 2, "Confirmed"),("CAND-003", "JD-103", "Screening", 0, "Pending"),("CAND-004", "JD-104", "Selected", -1, "Completed"),("CAND-005", "JD-108", "Shortlisted", 1, "Confirmed"),("CAND-006", "JD-104", "Screening", 0, "Scheduled"),("CAND-007", "JD-110", "Rejected", -2, "Closed"),("CAND-008", "JD-103", "Applied", 3, "Scheduled"),("CAND-009", "JD-101", "Selected", -10, "Completed"),("CAND-010", "JD-106", "Screening", 1, "Scheduled")]
SAMPLE_TASKS = [("Send JD to Sankalp Raj", "Share the latest JD and collect the updated CV", "rec1", "High", "Open", 0),("Follow up with Aditi", "Call back for final salary expectation", "rec1", "Medium", "Pending", 1),("Interview preparation for Rohit", "Guide the candidate for the recruiter round", "rec2", "High", "Open", 0),("Collect documents from Anjali", "Need PAN and bank details", "rec2", "Medium", "Closed", -1),("Review no-show trend", "Review East team reschedules", "tleast", "High", "Open", 2),("Call Satyam Dev", "Candidate requested a callback", "rec3", "High", "Pending", 0),("Schedule Priya panel", "Align with manager availability", "rec3", "Medium", "Open", 1),("Share rejection feedback", "Close the loop for Kanani", "rec4", "Low", "Closed", -2),("Welcome joined candidate", "Add to joined tracker", "tlnorth", "Low", "Closed", -3),("Review daily funnel", "Prepare the team report", "manager1", "High", "Open", 0)]
SAMPLE_PUBLIC_NOTES = [("CAND-001", "rec1", "public", "Candidate confirmed current employment status and can attend the interview tomorrow at 11:00 AM.", -3),("CAND-001", "tlnorth", "public", "Salary expectation appears aligned. Final confirmation on shift preference is pending.", -2),("CAND-001", "rec1", "public", "JD shared on WhatsApp and acknowledged by the candidate.", -1),("CAND-001", "manager1", "public", "Keep this profile active. Closure probability is strong with timely follow-up.", -1),("CAND-001", "rec1", "public", "Candidate requested location discussion after the HR round.", -1),("CAND-001", "tlnorth", "public", "Feedback reviewed. Proceed with interview confirmation.", 0),("CAND-002", "rec1", "public", "Candidate expects ₹24k in hand. Budget alignment remains under discussion.", -2),("CAND-004", "rec2", "public", "Selected and awaiting joining date confirmation.", -4),("CAND-006", "rec3", "public", "Candidate performed well in screening. Manager feedback is positive.", -1),("CAND-009", "manager1", "public", "60-day payout monitoring has started for this joined profile.", -5)]
SAMPLE_PRIVATE_NOTES = [("CAND-001", "rec1", "private", "Candidate responds faster after 6:00 PM. Evening outreach is recommended.", -2),("CAND-001", "manager1", "private", "Likely to be a stable retention profile if managed patiently.", -1),("CAND-002", "rec1", "private", "Negotiation may be possible if incentives are explained clearly.", -1),("CAND-003", "rec2", "private", "Candidate seemed unclear about the role. Use a simpler explanation.", 0),("CAND-004", "rec2", "private", "Strong profile. Useful as a benchmark for similar JDs.", -3),("CAND-005", "rec3", "private", "Background noise affected the call. Evening callback is preferable.", -1),("CAND-006", "manager1", "private", "Keep the team lead informed if this profile becomes high priority.", 0),("CAND-007", "rec4", "private", "Interest level appears low. Limit time investment.", -4),("CAND-009", "manager1", "private", "Useful joined case for payout process demonstration.", -8),("CAND-010", "rec3", "private", "Candidate may be better aligned to JD-103 than JD-106.", -1)]
SAMPLE_MESSAGES = [("manager1", "tlnorth", "Please review all new public notes on Sankalp today.", -1),("tlnorth", "rec1", "Reviewed. Please push for confirmation and update note history.", -1),("rec1", "tlnorth", "Done. Candidate is responsive now.", 0),("tleast", "rec3", "Need the East team interview tracker by evening.", 0),("rec3", "tleast", "Working on it. Priya and Satyam are updated.", 0),("manager1", "rec4", "Please clean rejection reasons in your pipeline.", -2),("rec4", "manager1", "Working on it today.", -2),("rec2", "tlnorth", "Anjali is selected. Documents are pending.", -3),("manager1", "rec2", "Good. Add a note and move to joined monitoring.", -3),("rec3", "manager1", "Need approval for the interview reschedule trend review.", -1)]


def sql_compat(query: str) -> str:
    if not USE_POSTGRES:
        return query
    q = query.replace('?', '%s').replace("date('now')", 'CURRENT_DATE')
    q = re.sub(r'datetime\(([^)]+)\)', r'CAST(\1 AS timestamp)', q)
    return q


def get_db():
    if 'db' not in g:
        if USE_POSTGRES:
            if psycopg2 is None:
                raise RuntimeError('psycopg2-binary is required when DATABASE_URL is used.')
            conn_str = DATABASE_URL if 'sslmode=' in DATABASE_URL else DATABASE_URL + ('&' if '?' in DATABASE_URL else '?') + 'sslmode=require'
            g.db = psycopg2.connect(conn_str, cursor_factory=RealDictCursor)
            g.db.autocommit = False
        else:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db


def query_db(query, params=(), one=False):
    cur = get_db().cursor()
    cur.execute(sql_compat(query), params)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, params=()):
    db = get_db()
    cur = db.cursor()
    q = sql_compat(query)
    if USE_POSTGRES and query.strip().lower().startswith('insert into'):
        cur.execute(q + ' RETURNING id', params)
        row = cur.fetchone()
        db.commit()
        cur.close()
        return row['id'] if row else None
    cur.execute(q, params)
    db.commit()
    out = getattr(cur, 'lastrowid', None)
    cur.close()
    return out


def init_db():
    if USE_POSTGRES:
        stmts = [
            "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, full_name TEXT, designation TEXT, role TEXT, team TEXT, manager_username TEXT, password TEXT)",
            "CREATE TABLE IF NOT EXISTS jds (id SERIAL PRIMARY KEY, code TEXT UNIQUE, title TEXT, location TEXT, experience_required TEXT, payout INTEGER, payout_days INTEGER, status TEXT)",
            "CREATE TABLE IF NOT EXISTS candidates (id SERIAL PRIMARY KEY, code TEXT UNIQUE, full_name TEXT, phone TEXT, location TEXT, experience TEXT, status TEXT, recruiter_username TEXT, tl_username TEXT, jd_code TEXT, qualification TEXT, created_at TEXT)",
            "CREATE TABLE IF NOT EXISTS submissions (id SERIAL PRIMARY KEY, candidate_code TEXT, jd_code TEXT, recruiter_username TEXT, status TEXT, submitted_at TEXT)",
            "CREATE TABLE IF NOT EXISTS interviews (id SERIAL PRIMARY KEY, candidate_code TEXT, jd_code TEXT, stage TEXT, scheduled_at TEXT, status TEXT)",
            "CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, title TEXT, description TEXT, assigned_to TEXT, priority TEXT, status TEXT, due_at TEXT)",
            "CREATE TABLE IF NOT EXISTS notes (id SERIAL PRIMARY KEY, candidate_code TEXT, username TEXT, note_type TEXT, body TEXT, created_at TEXT)",
            "CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, username TEXT, candidate_code TEXT, title TEXT, message TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)",
            "CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender_username TEXT, recipient_username TEXT, body TEXT, created_at TEXT)",
        ]
        db = get_db(); cur = db.cursor()
        for s in stmts: cur.execute(s)
        db.commit(); cur.close()
    else:
        db = sqlite3.connect(DB_PATH); cur = db.cursor()
        stmts = [
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, full_name TEXT, designation TEXT, role TEXT, team TEXT, manager_username TEXT, password TEXT)",
            "CREATE TABLE IF NOT EXISTS jds (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, title TEXT, location TEXT, experience_required TEXT, payout INTEGER, payout_days INTEGER, status TEXT)",
            "CREATE TABLE IF NOT EXISTS candidates (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, full_name TEXT, phone TEXT, location TEXT, experience TEXT, status TEXT, recruiter_username TEXT, tl_username TEXT, jd_code TEXT, qualification TEXT, created_at TEXT)",
            "CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_code TEXT, jd_code TEXT, recruiter_username TEXT, status TEXT, submitted_at TEXT)",
            "CREATE TABLE IF NOT EXISTS interviews (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_code TEXT, jd_code TEXT, stage TEXT, scheduled_at TEXT, status TEXT)",
            "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, assigned_to TEXT, priority TEXT, status TEXT, due_at TEXT)",
            "CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_code TEXT, username TEXT, note_type TEXT, body TEXT, created_at TEXT)",
            "CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, candidate_code TEXT, title TEXT, message TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)",
            "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_username TEXT, recipient_username TEXT, body TEXT, created_at TEXT)",
        ]
        for s in stmts: cur.execute(s)
        db.commit(); db.close()


def seed_demo_data():
    existing = query_db('SELECT COUNT(*) as c FROM users', one=True)
    if existing and existing['c'] > 0:
        return
    for row in SAMPLE_USERS:
        execute_db('INSERT INTO users (username, full_name, designation, role, team, manager_username, password) VALUES (?, ?, ?, ?, ?, ?, ?)', row)
    for row in SAMPLE_JDS:
        execute_db('INSERT INTO jds (code, title, location, experience_required, payout, payout_days, status) VALUES (?, ?, ?, ?, ?, ?, ?)', row)
    now = datetime.now()
    for row in SAMPLE_CANDIDATES:
        created_at = (now - timedelta(days=random.randint(1, 15), hours=random.randint(0, 18))).strftime('%Y-%m-%d %H:%M')
        execute_db('INSERT INTO candidates (code, full_name, phone, location, experience, status, recruiter_username, tl_username, jd_code, qualification, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', row + (created_at,))
    for candidate_code, jd_code, recruiter, status, offset_days in SAMPLE_SUBMISSIONS:
        execute_db('INSERT INTO submissions (candidate_code, jd_code, recruiter_username, status, submitted_at) VALUES (?, ?, ?, ?, ?)', (candidate_code, jd_code, recruiter, status, (now + timedelta(days=offset_days)).strftime('%Y-%m-%d %H:%M')))
    for candidate_code, jd_code, stage, day_offset, status in SAMPLE_INTERVIEWS:
        execute_db('INSERT INTO interviews (candidate_code, jd_code, stage, scheduled_at, status) VALUES (?, ?, ?, ?, ?)', (candidate_code, jd_code, stage, (now + timedelta(days=day_offset, hours=random.randint(9, 17))).strftime('%Y-%m-%d %H:%M'), status))
    for title, desc, assigned, priority, status, day_offset in SAMPLE_TASKS:
        execute_db('INSERT INTO tasks (title, description, assigned_to, priority, status, due_at) VALUES (?, ?, ?, ?, ?, ?)', (title, desc, assigned, priority, status, (now + timedelta(days=day_offset, hours=random.randint(8, 18))).strftime('%Y-%m-%d %H:%M')))
    for candidate_code, username, note_type, body, day_offset in SAMPLE_PUBLIC_NOTES + SAMPLE_PRIVATE_NOTES:
        execute_db('INSERT INTO notes (candidate_code, username, note_type, body, created_at) VALUES (?, ?, ?, ?, ?)', (candidate_code, username, note_type, body, (now + timedelta(days=day_offset, hours=random.randint(8, 20), minutes=random.randint(1, 55))).strftime('%Y-%m-%d %H:%M')))
    for sender, recipient, body, day_offset in SAMPLE_MESSAGES:
        execute_db('INSERT INTO messages (sender_username, recipient_username, body, created_at) VALUES (?, ?, ?, ?)', (sender, recipient, body, (now + timedelta(days=day_offset, hours=random.randint(8, 20), minutes=random.randint(1, 55))).strftime('%Y-%m-%d %H:%M')))
    candidates = {r['code']: r for r in query_db('SELECT * FROM candidates')}
    for candidate_code, username, _note_type, _body, day_offset in SAMPLE_PUBLIC_NOTES:
        c = candidates.get(candidate_code)
        if c:
            title = f"Public note updated for {c['full_name']}"
            msg = f"{username} added a note. Review the latest feedback for {c['full_name']}."
            created = (now + timedelta(days=day_offset, hours=random.randint(8, 20), minutes=random.randint(1, 55))).strftime('%Y-%m-%d %H:%M')
            for target in [c['recruiter_username'], c['tl_username']]:
                execute_db('INSERT INTO notifications (username, candidate_code, title, message, is_read, created_at) VALUES (?, ?, ?, ?, 0, ?)', (target, candidate_code, title, msg, created))


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('username'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper


def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user['role'] != 'manager':
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def current_user():
    uname = session.get('impersonated_as') or session.get('username')
    return query_db('SELECT * FROM users WHERE username = ?', (uname,), one=True) if uname else None


def visible_private_notes(candidate_code, user):
    if user['role'] == 'manager':
        return query_db("SELECT n.*, u.full_name, u.designation FROM notes n JOIN users u ON u.username = n.username WHERE n.candidate_code = ? AND n.note_type = 'private' ORDER BY datetime(n.created_at) DESC", (candidate_code,))
    return query_db("SELECT n.*, u.full_name, u.designation FROM notes n JOIN users u ON u.username = n.username WHERE n.candidate_code = ? AND n.note_type = 'private' AND n.username = ? ORDER BY datetime(n.created_at) DESC", (candidate_code, user['username']))

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop('db', None)
    if db is not None: db.close()

@app.context_processor
def inject_globals():
    user = current_user(); unread = 0
    if user:
        row = query_db('SELECT COUNT(*) as c FROM notifications WHERE username = ? AND is_read = 0', (user['username'],), one=True)
        unread = row['c'] if row else 0
    return {'sidebar_items': SIDEBAR_ITEMS,'current_user_data': user,'unread_notifications': unread,'now': datetime.now(),'all_recruiters': query_db("SELECT username, full_name FROM users WHERE role='recruiter' ORDER BY full_name"),'all_assignees': query_db('SELECT username, full_name, designation FROM users ORDER BY role, full_name'),'all_jds': query_db('SELECT code, title FROM jds ORDER BY title'),'all_candidates_basic': query_db('SELECT code, full_name FROM candidates ORDER BY full_name')}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = query_db('SELECT * FROM users WHERE username = ? AND password = ?', (request.form.get('username','').strip(), request.form.get('password','').strip()), one=True)
        if user:
            session['username'] = user['username']; flash(f"Welcome, {user['full_name']}.", 'success'); return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', demo_users=query_db('SELECT username, full_name, designation, role FROM users ORDER BY role, id'))

@app.route('/logout')
def logout():
    session.clear(); flash('Logged out successfully.', 'info'); return redirect(url_for('login'))

@app.route('/')
@login_required
def root(): return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user()
    return render_template('dashboard.html', total_profiles=query_db('SELECT COUNT(*) as c FROM candidates', one=True)['c'], today_calls=52, interviews_today=query_db("SELECT COUNT(*) as c FROM interviews WHERE date(scheduled_at) = date('now')", one=True)['c'], active_managers=query_db("SELECT COUNT(*) as c FROM users WHERE role IN ('manager','tl')", one=True)['c'], recent_activity=query_db("SELECT c.full_name, c.status, c.code, c.created_at, u.full_name AS recruiter_name FROM candidates c LEFT JOIN users u ON u.username = c.recruiter_username ORDER BY datetime(c.created_at) DESC LIMIT 6"), due_tasks=query_db("SELECT t.*, u.full_name FROM tasks t LEFT JOIN users u ON u.username = t.assigned_to ORDER BY CASE t.status WHEN 'Open' THEN 1 WHEN 'Pending' THEN 2 ELSE 3 END, datetime(t.due_at) ASC LIMIT 6"), manager_monitoring=query_db("SELECT u.full_name, u.designation, (SELECT COUNT(*) FROM candidates c WHERE c.recruiter_username = u.username) as candidate_count, (SELECT COUNT(*) FROM tasks t WHERE t.assigned_to = u.username AND t.status != 'Closed') as open_tasks FROM users u WHERE u.role IN ('recruiter','tl') ORDER BY u.role DESC, candidate_count DESC LIMIT 6"), unread_notes=query_db("SELECT n.title, n.message, n.created_at, c.full_name FROM notifications n LEFT JOIN candidates c ON c.code = n.candidate_code WHERE n.username = ? ORDER BY datetime(n.created_at) DESC LIMIT 5", (user['username'],)))

@app.route('/candidates')
@login_required
def candidates():
    q=request.args.get('q','').strip(); recruiter=request.args.get('recruiter','').strip(); status=request.args.get('status','').strip(); conditions=[]; params=[]
    sql="SELECT c.*, r.full_name AS recruiter_name, r.username AS recruiter_code, t.full_name AS tl_name, j.title AS jd_title FROM candidates c LEFT JOIN users r ON r.username = c.recruiter_username LEFT JOIN users t ON t.username = c.tl_username LEFT JOIN jds j ON j.code = c.jd_code"
    if q: conditions.append('(c.full_name LIKE ? OR c.phone LIKE ? OR c.jd_code LIKE ? OR c.location LIKE ? OR c.status LIKE ?)'); params.extend([f'%{q}%']*5)
    if recruiter: conditions.append('c.recruiter_username = ?'); params.append(recruiter)
    if status: conditions.append('c.status = ?'); params.append(status)
    if conditions: sql += ' WHERE ' + ' AND '.join(conditions)
    sql += ' ORDER BY datetime(c.created_at) DESC'
    return render_template('candidates.html', candidates=query_db(sql, params), recruiters=query_db("SELECT username, full_name FROM users WHERE role='recruiter' ORDER BY full_name"), statuses=[r['status'] for r in query_db('SELECT DISTINCT status FROM candidates ORDER BY status')], q=q, current_recruiter=recruiter, current_status=status)

@app.post('/candidate/add')
@login_required
def add_candidate():
    f = request.form; full_name=f.get('full_name','').strip(); phone=f.get('phone','').strip(); recruiter_username=f.get('recruiter_username','').strip();
    if not full_name or not phone: flash('Candidate name and phone are required.', 'danger'); return redirect(url_for('candidates'))
    tl = query_db('SELECT manager_username FROM users WHERE username = ?', (recruiter_username,), one=True)
    code = f"CAND-{query_db('SELECT COUNT(*) as c FROM candidates', one=True)['c'] + 1:03d}"
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    execute_db('INSERT INTO candidates (code, full_name, phone, location, experience, status, recruiter_username, tl_username, jd_code, qualification, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (code, full_name, phone, f.get('location','').strip(), f.get('experience','').strip(), f.get('status','Applied').strip() or 'Applied', recruiter_username, tl['manager_username'] if tl else '', f.get('jd_code','').strip(), f.get('qualification','').strip() or 'Not Specified', created_at))
    if f.get('jd_code','').strip(): execute_db('INSERT INTO submissions (candidate_code, jd_code, recruiter_username, status, submitted_at) VALUES (?, ?, ?, ?, ?)', (code, f.get('jd_code','').strip(), recruiter_username, f.get('status','Applied').strip() or 'Applied', created_at))
    flash(f'Candidate {full_name} created successfully.', 'success'); return redirect(url_for('candidates'))

@app.route('/candidate/<candidate_code>')
@login_required
def candidate_detail(candidate_code):
    candidate = query_db("SELECT c.*, r.full_name AS recruiter_name, t.full_name AS tl_name, j.title AS jd_title, j.payout FROM candidates c LEFT JOIN users r ON r.username = c.recruiter_username LEFT JOIN users t ON t.username = c.tl_username LEFT JOIN jds j ON j.code = c.jd_code WHERE c.code = ?", (candidate_code,), one=True)
    if not candidate: abort(404)
    return render_template('candidate_detail.html', candidate=candidate, public_notes=query_db("SELECT n.*, u.full_name, u.designation FROM notes n JOIN users u ON u.username = n.username WHERE n.candidate_code = ? AND n.note_type = 'public' ORDER BY datetime(n.created_at) DESC", (candidate_code,)), private_notes=visible_private_notes(candidate_code, current_user()), related_notifications=query_db('SELECT * FROM notifications WHERE candidate_code = ? ORDER BY datetime(created_at) DESC LIMIT 8', (candidate_code,)), timeline=query_db("SELECT 'Submission' AS event_type, status AS label, jd_code, submitted_at AS event_time FROM submissions WHERE candidate_code = ? UNION ALL SELECT 'Interview' AS event_type, stage || ' / ' || status AS label, jd_code, scheduled_at AS event_time FROM interviews WHERE candidate_code = ? UNION ALL SELECT 'Note' AS event_type, note_type AS label, candidate_code AS jd_code, created_at AS event_time FROM notes WHERE candidate_code = ? ORDER BY event_time DESC", (candidate_code, candidate_code, candidate_code)))

@app.post('/candidate/<candidate_code>/add-note')
@login_required
def add_note(candidate_code):
    user=current_user(); body=request.form.get('body','').strip(); note_type=request.form.get('note_type','public').strip();
    if not body: flash('Note text is required.', 'danger'); return redirect(url_for('candidate_detail', candidate_code=candidate_code))
    created_at=datetime.now().strftime('%Y-%m-%d %H:%M'); execute_db('INSERT INTO notes (candidate_code, username, note_type, body, created_at) VALUES (?, ?, ?, ?, ?)', (candidate_code, user['username'], note_type, body, created_at))
    candidate=query_db('SELECT * FROM candidates WHERE code = ?', (candidate_code,), one=True)
    if candidate and note_type=='public':
        for target in [candidate['recruiter_username'], candidate['tl_username']]:
            if target: execute_db('INSERT INTO notifications (username, candidate_code, title, message, is_read, created_at) VALUES (?, ?, ?, ?, 0, ?)', (target, candidate_code, f"Public note updated for {candidate['full_name']}", f"{user['full_name']} added a public note.", created_at))
    flash('Note saved successfully.', 'success'); return redirect(url_for('candidate_detail', candidate_code=candidate_code))

@app.route('/jds')
@login_required
def jds():
    q=request.args.get('q','').strip(); status=request.args.get('status','').strip(); sql='SELECT * FROM jds'; cond=[]; params=[]
    if q: cond.append('(code LIKE ? OR title LIKE ? OR location LIKE ?)'); params.extend([f'%{q}%']*3)
    if status: cond.append('status = ?'); params.append(status)
    if cond: sql += ' WHERE ' + ' AND '.join(cond)
    sql += ' ORDER BY title'
    return render_template('jds.html', jds=query_db(sql, params), status_choices=[r['status'] for r in query_db('SELECT DISTINCT status FROM jds ORDER BY status')], q=q, current_status=status)

@app.post('/jd/add')
@login_required
def add_jd():
    f=request.form; code=f.get('code','').strip(); title=f.get('title','').strip();
    if not code or not title: flash('JD code and title are required.', 'danger'); return redirect(url_for('jds'))
    execute_db('INSERT INTO jds (code, title, location, experience_required, payout, payout_days, status) VALUES (?, ?, ?, ?, ?, ?, ?)', (code, title, f.get('location','').strip(), f.get('experience_required','').strip(), int(f.get('payout','0') or 0), int(f.get('payout_days','0') or 0), f.get('status','Open').strip() or 'Open'))
    flash(f'JD {code} created successfully.', 'success'); return redirect(url_for('jds'))

@app.route('/interviews')
@login_required
def interviews():
    stage=request.args.get('stage','').strip();
    base="SELECT i.*, c.full_name, c.phone, j.title AS jd_title FROM interviews i LEFT JOIN candidates c ON c.code = i.candidate_code LEFT JOIN jds j ON j.code = i.jd_code"
    sql = base + (' WHERE i.stage = ?' if stage else '') + ' ORDER BY datetime(i.scheduled_at) DESC'
    return render_template('interviews.html', interviews=query_db(sql, (stage,) if stage else ()), stage_choices=[r['stage'] for r in query_db('SELECT DISTINCT stage FROM interviews ORDER BY stage')], current_stage=stage)

@app.post('/interview/add')
@login_required
def add_interview():
    f=request.form; candidate_code=f.get('candidate_code','').strip(); scheduled_at=f.get('scheduled_at','').strip();
    if not candidate_code or not scheduled_at: flash('Candidate and schedule time are required.', 'danger'); return redirect(url_for('interviews'))
    execute_db('INSERT INTO interviews (candidate_code, jd_code, stage, scheduled_at, status) VALUES (?, ?, ?, ?, ?)', (candidate_code, f.get('jd_code','').strip(), f.get('stage','').strip() or 'Screening', scheduled_at, f.get('status','').strip() or 'Scheduled'))
    flash('Interview scheduled successfully.', 'success'); return redirect(url_for('interviews'))

@app.route('/tasks')
@login_required
def tasks():
    assignee=request.args.get('assignee','').strip(); sql="SELECT t.*, u.full_name FROM tasks t LEFT JOIN users u ON u.username = t.assigned_to" + (' WHERE t.assigned_to = ?' if assignee else '') + " ORDER BY CASE t.status WHEN 'Open' THEN 1 WHEN 'Pending' THEN 2 ELSE 3 END, datetime(t.due_at) ASC"
    return render_template('tasks.html', tasks=query_db(sql, (assignee,) if assignee else ()), assignees=query_db('SELECT username, full_name FROM users ORDER BY full_name'), current_assignee=assignee)

@app.post('/task/add')
@login_required
def add_task():
    f=request.form; title=f.get('title','').strip(); assigned_to=f.get('assigned_to','').strip(); due_at=f.get('due_at','').strip();
    if not title or not assigned_to or not due_at: flash('Task title, assignee, and due date are required.', 'danger'); return redirect(url_for('tasks'))
    execute_db('INSERT INTO tasks (title, description, assigned_to, priority, status, due_at) VALUES (?, ?, ?, ?, ?, ?)', (title, f.get('description','').strip(), assigned_to, f.get('priority','Medium').strip() or 'Medium', f.get('status','Open').strip() or 'Open', due_at))
    flash('Task created successfully.', 'success'); return redirect(url_for('tasks'))

@app.route('/submissions')
@login_required
def submissions(): return render_template('submissions.html', submissions=query_db("SELECT s.*, c.full_name, j.title AS jd_title, u.full_name AS recruiter_name FROM submissions s LEFT JOIN candidates c ON c.code = s.candidate_code LEFT JOIN jds j ON j.code = s.jd_code LEFT JOIN users u ON u.username = s.recruiter_username ORDER BY datetime(s.submitted_at) DESC"))

@app.route('/notifications')
@login_required
def notifications_page():
    user=current_user(); rows=query_db('SELECT * FROM notifications WHERE username = ? ORDER BY datetime(created_at) DESC', (user['username'],)); execute_db('UPDATE notifications SET is_read = 1 WHERE username = ?', (user['username'],)); return render_template('notifications.html', notifications=rows)

@app.route('/chat', methods=['GET','POST'])
@login_required
def chat_page():
    user=current_user(); users=query_db('SELECT username, full_name, designation, role FROM users WHERE username != ? ORDER BY role, full_name', (user['username'],)); selected=request.args.get('user','').strip() or (users[0]['username'] if users else '')
    if request.method=='POST' and request.form.get('recipient_username','').strip() and request.form.get('body','').strip():
        execute_db('INSERT INTO messages (sender_username, recipient_username, body, created_at) VALUES (?, ?, ?, ?)', (user['username'], request.form.get('recipient_username').strip(), request.form.get('body').strip(), datetime.now().strftime('%Y-%m-%d %H:%M'))); flash('Message sent.', 'success'); return redirect(url_for('chat_page', user=request.form.get('recipient_username').strip()))
    convo=query_db("SELECT m.*, s.full_name AS sender_name FROM messages m LEFT JOIN users s ON s.username = m.sender_username WHERE (sender_username = ? AND recipient_username = ?) OR (sender_username = ? AND recipient_username = ?) ORDER BY datetime(created_at) ASC", (user['username'], selected, selected, user['username'])) if selected else []
    return render_template('chat.html', users=users, selected_user=selected, messages=convo)

@app.route('/admin')
@login_required
@manager_required
def admin_page(): return render_template('admin.html', users=query_db('SELECT * FROM users ORDER BY role, team, full_name'), notes_count=query_db('SELECT username, COUNT(*) AS total_notes FROM notes GROUP BY username ORDER BY total_notes DESC'))

@app.route('/admin/impersonate/<username>')
@login_required
@manager_required
def impersonate(username):
    target=query_db('SELECT * FROM users WHERE username = ?', (username,), one=True); manager=query_db('SELECT * FROM users WHERE username = ?', (session.get('username'),), one=True)
    if not target or not manager: abort(404)
    session['impersonator']=manager['username']; session['impersonated_as']=username; flash(f"Viewing the application as {target['full_name']}.", 'info'); return redirect(url_for('dashboard'))

@app.route('/admin/stop-impersonation')
@login_required
def stop_impersonation():
    if session.get('impersonator'):
        session['username']=session.get('impersonator'); session.pop('impersonated_as', None); session.pop('impersonator', None); flash('Returned to the manager account.', 'success')
    return redirect(url_for('admin_page'))

@app.route('/module/<slug>')
@login_required
def module_page(slug):
    module=MODULE_SUMMARIES.get(slug)
    if not module: abort(404)
    dialer_candidates=query_db("SELECT c.code, c.full_name, c.phone, c.status, c.location, c.experience, r.full_name AS recruiter_name, t.full_name AS tl_name FROM candidates c LEFT JOIN users r ON r.username = c.recruiter_username LEFT JOIN users t ON t.username = c.tl_username ORDER BY datetime(c.created_at) DESC") if slug=='dialer' else []
    meeting_feed=[{'name':'Ritika joined','time':'03:00 PM','state':'Joined'},{'name':'Mohit joined','time':'03:02 PM','state':'Joined'},{'name':'Barnali left','time':'03:11 PM','state':'Left'},{'name':'Neha joined','time':'03:14 PM','state':'Joined'}] if slug=='meeting-room' else []
    return render_template('module_page.html', module=module, slug=slug, dialer_candidates=dialer_candidates, meeting_feed=meeting_feed)

@app.route('/blueprint')
@login_required
def blueprint_page():
    return render_template('blueprint.html', blueprint_text=open(os.path.join(BASE_DIR,'docs','MEGA_BLUEPRINT_120_PLUS_FEATURES.md'), encoding='utf-8').read(), context_text=open(os.path.join(BASE_DIR,'docs','CROSS_CHAT_MASTER_CONTEXT.txt'), encoding='utf-8').read())

@app.route('/preview')
def preview_page(): return render_template('preview.html', demo_users=query_db('SELECT username, full_name, designation, role FROM users ORDER BY role, id'))

with app.app_context():
    init_db()
    seed_demo_data()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
