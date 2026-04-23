from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
import sqlite3
import os
import re
import sys
from datetime import date, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash


def _base_dir():
    """Return the directory that contains the app's data files.
    When bundled by PyInstaller, templates live in sys._MEIPASS but the
    database must live next to the .exe (sys.executable), not the temp dir."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _bundle_dir():
    """Templates/static assets — extracted temp dir when bundled, else source dir."""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


app = Flask(__name__,
            template_folder=os.path.join(_bundle_dir(), 'templates'),
            static_folder=os.path.join(_bundle_dir(), 'static'))
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-before-hosting-on-network')
app.permanent_session_lifetime = timedelta(days=30)

# Share this URL with anyone you want to register — keep it out of browser history
REGISTER_SECRET = os.environ.get('REGISTER_SECRET', 'myregister')

DB_PATH = os.path.join(_base_dir(), 'food_diary.db')
VALID_MEALS = {'breakfast', 'snack1', 'lunch', 'snack2', 'dinner'}
MEAL_ORDER  = ['breakfast', 'snack1', 'lunch', 'snack2', 'dinner']
MEAL_LABELS = {
    'breakfast': 'Breakfast',
    'snack1':    'Snack 1',
    'lunch':     'Lunch',
    'snack2':    'Snack 2',
    'dinner':    'Dinner',
}


# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                meal TEXT NOT NULL,
                food_name TEXT NOT NULL,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_user_date ON entries(user_id, date)')
        conn.commit()
        # Migrate single-user installs: add user_id column if absent
        cols = [r[1] for r in conn.execute('PRAGMA table_info(entries)').fetchall()]
        if 'user_id' not in cols:
            conn.execute('ALTER TABLE entries ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE')
            conn.commit()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'unauthorized'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


# ── PWA files (public, no auth) ───────────────────────────────────────────────

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Food Diary",
        "short_name": "Food Diary",
        "description": "Track your daily meals and snacks",
        "start_url": "/",
        "display": "standalone",
        "orientation": "portrait",
        "theme_color": "#22c55e",
        "background_color": "#f3f4f6",
        "icons": [
            {"src": "/static/icons/icon-72.png",  "sizes": "72x72",   "type": "image/png"},
            {"src": "/static/icons/icon-96.png",  "sizes": "96x96",   "type": "image/png"},
            {"src": "/static/icons/icon-128.png", "sizes": "128x128", "type": "image/png"},
            {"src": "/static/icons/icon-144.png", "sizes": "144x144", "type": "image/png"},
            {"src": "/static/icons/icon-152.png", "sizes": "152x152", "type": "image/png"},
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/icons/icon-384.png", "sizes": "384x384", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "categories": ["health", "lifestyle"],
    })


@app.route('/sw.js')
def service_worker():
    return send_from_directory(app.static_folder, 'sw.js',
                               mimetype='application/javascript')


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html', error=None)


@app.route('/login', methods=['POST'])
def login():
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if user and check_password_hash(user['password_hash'], password):
        session.clear()
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        return redirect(url_for('index'))
    return render_template('login.html', error='Invalid username or password.')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/register/<secret>', methods=['GET'])
def register_page(secret):
    if secret != REGISTER_SECRET:
        return '', 404
    return render_template('register.html', secret=secret, error=None, success=None)


@app.route('/register/<secret>', methods=['POST'])
def register(secret):
    if secret != REGISTER_SECRET:
        return '', 404

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    confirm  = request.form.get('confirm') or ''

    def fail(msg):
        return render_template('register.html', secret=secret, error=msg, success=None)

    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return fail('Username must be 3–20 characters: letters, numbers, underscores only.')
    if len(password) < 8:
        return fail('Password must be at least 8 characters.')
    if password != confirm:
        return fail('Passwords do not match.')

    with get_db() as conn:
        if conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            return fail('That username is already taken.')
        conn.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, generate_password_hash(password))
        )
        conn.commit()

    return render_template('register.html', secret=secret, error=None,
                           success=f'Account "{username}" created. You can now sign in.')


# ── Main page ─────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session['username'])


# ── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/entries')
@login_required
def get_entries():
    day = request.args.get('date', date.today().isoformat())
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM entries WHERE user_id = ? AND date = ? ORDER BY meal, created_at',
            (session['user_id'], day)
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/entries', methods=['POST'])
@login_required
def add_entry():
    data = request.get_json()
    food_name = (data.get('food_name') or '').strip()
    if not food_name:
        return jsonify({'error': 'food_name is required'}), 400
    meal = data.get('meal', '')
    if meal not in VALID_MEALS:
        return jsonify({'error': 'invalid meal'}), 400
    with get_db() as conn:
        cur = conn.execute(
            'INSERT INTO entries (user_id, date, meal, food_name, notes) VALUES (?, ?, ?, ?, ?)',
            (session['user_id'], data.get('date', date.today().isoformat()),
             meal, food_name, (data.get('notes') or '').strip())
        )
        conn.commit()
        row = conn.execute('SELECT * FROM entries WHERE id = ?', (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_entry(entry_id):
    with get_db() as conn:
        conn.execute('DELETE FROM entries WHERE id = ? AND user_id = ?', (entry_id, session['user_id']))
        conn.commit()
    return '', 204


@app.route('/api/entries/<int:entry_id>', methods=['PUT'])
@login_required
def update_entry(entry_id):
    data = request.get_json()
    food_name = (data.get('food_name') or '').strip()
    if not food_name:
        return jsonify({'error': 'food_name is required'}), 400
    with get_db() as conn:
        conn.execute(
            'UPDATE entries SET food_name = ?, notes = ? WHERE id = ? AND user_id = ?',
            (food_name, (data.get('notes') or '').strip(), entry_id, session['user_id'])
        )
        conn.commit()
        row = conn.execute('SELECT * FROM entries WHERE id = ? AND user_id = ?',
                           (entry_id, session['user_id'])).fetchone()
    if row is None:
        return jsonify({'error': 'not found'}), 404
    return jsonify(dict(row))


# ── Report & Export ───────────────────────────────────────────────────────────

def _fetch_range(user_id, from_date, to_date):
    with get_db() as conn:
        return conn.execute(
            '''SELECT date, meal, food_name, notes FROM entries
               WHERE user_id = ? AND date >= ? AND date <= ?
               ORDER BY date, meal, created_at''',
            (user_id, from_date, to_date)
        ).fetchall()


@app.route('/report')
@login_required
def report():
    from_date = request.args.get('from', date.today().isoformat())
    to_date   = request.args.get('to',   date.today().isoformat())
    rows = _fetch_range(session['user_id'], from_date, to_date)

    # Build {date: {meal: [entries]}} structure in display order
    from collections import defaultdict
    data = {}
    for row in rows:
        d, m = row['date'], row['meal']
        if d not in data:
            data[d] = {k: [] for k in MEAL_ORDER}
        if m in data[d]:
            data[d][m].append({'food': row['food_name'], 'notes': row['notes']})

    # Summary: total items per meal across the range
    summary = {m: 0 for m in MEAL_ORDER}
    total   = 0
    for day_meals in data.values():
        for meal, items in day_meals.items():
            summary[meal] += len(items)
            total += len(items)

    return render_template('report.html',
                           data=data,
                           from_date=from_date,
                           to_date=to_date,
                           meal_order=MEAL_ORDER,
                           meal_labels=MEAL_LABELS,
                           summary=summary,
                           total=total,
                           username=session['username'])


@app.route('/api/export')
@login_required
def export_csv():
    import csv, io
    from flask import Response

    from_date = request.args.get('from', date.today().isoformat())
    to_date   = request.args.get('to',   date.today().isoformat())
    rows = _fetch_range(session['user_id'], from_date, to_date)

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['Date', 'Meal', 'Food', 'Notes'])
    for row in rows:
        writer.writerow([
            row['date'],
            MEAL_LABELS.get(row['meal'], row['meal']),
            row['food_name'],
            row['notes'] or '',
        ])

    filename = f"food_diary_{from_date}_to_{to_date}.csv"
    return Response(
        out.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


if __name__ == '__main__':
    import threading, webbrowser, time

    init_db()
    print(f'\nFood Diary running at http://localhost:5000')
    print(f'Register URL:          http://localhost:5000/register/{REGISTER_SECRET}')
    print(f'Other devices:         http://<your-ip>:5000')
    print(f'Database:              {DB_PATH}\n')

    if hasattr(sys, '_MEIPASS'):
        # Auto-open browser when running as bundled exe
        def _open():
            time.sleep(1.5)
            webbrowser.open('http://localhost:5000')
        threading.Thread(target=_open, daemon=True).start()

    app.run(host='0.0.0.0', port=5000, debug=False)
