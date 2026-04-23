# Food Diary

A self-hosted food diary web app for tracking daily meals and snacks. Runs entirely on your home network — no cloud, no subscriptions, no data leaving your house.

Built with Python + Flask + SQLite. Supports multiple users, printable reports, CSV export, and can be installed as a Progressive Web App (PWA) on any phone.

---

## Features

- **5 meal slots per day** — Breakfast, Snack 1, Lunch, Snack 2, Dinner
- **Multi-user** — each user sees only their own diary
- **Date navigation** — browse any day with prev/next arrows or date picker
- **Edit & delete** entries inline (hover to reveal buttons)
- **Printable reports** — clean print layout for any date range
- **CSV export** — download your data for any date range
- **Progressive Web App** — installable on iPhone and Android, works over your home Wi-Fi
- **Single-file database** — everything stored in `food_diary.db` next to the app
- **Standalone Windows exe** — build with PyInstaller, no Python needed on target machine

---

## Requirements

- Python 3.8 or newer
- Flask (`pip install flask`)

To build the Windows exe:
- PyInstaller (`pip install pyinstaller`)
- Pillow (`pip install pillow`) — only needed to regenerate icons

---

## Quick Start

### Run from source

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

Then open **http://localhost:5000** in your browser.

On first run the database is created automatically. Register your first account at the hidden registration URL printed in the console.

### Windows — double-click launcher

Double-click **`start.bat`**. It installs Flask automatically if needed, then starts the server.

---

## Configuration

Two settings at the top of `app.py` (or via environment variables):

| Setting | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-this-before-hosting-on-network` | Signs session cookies — change before exposing to your network |
| `REGISTER_SECRET` | `myregister` | The secret path segment for the registration page |

**Registration URL:** `http://localhost:5000/register/<REGISTER_SECRET>`

This URL is intentionally not linked anywhere. Share it only with people you want to give access. Anyone who doesn't know it gets a 404.

Set via environment variable (recommended):

```bash
# Windows
set SECRET_KEY=your-random-secret-key
set REGISTER_SECRET=your-secret-word
python app.py

# Linux / macOS
SECRET_KEY=your-random-secret-key REGISTER_SECRET=your-secret-word python app.py
```

---

## Accessing from other devices

The server listens on all interfaces (`0.0.0.0:5000`). Find your machine's local IP address and open:

```
http://192.168.1.x:5000
```

Your IP is printed in the console when the app starts.

---

## Installing as a PWA on your phone

The app is a full PWA — it can be added to your home screen and behaves like a native app.

**Android (Chrome):**
1. Open the app URL in Chrome
2. Tap ⋮ menu → **Add to Home Screen**

**iPhone (Safari):**
1. Open the app URL in Safari
2. Tap the **Share** button → **Add to Home Screen**

When your phone is away from home Wi-Fi, a friendly offline page is shown instead of a browser error.

---

## Building the Windows exe

```bat
build.bat
```

This produces `dist\food_diary.exe` — a single self-contained executable (~14 MB). Copy it to any Windows machine and run it. No Python installation required.

The database (`food_diary.db`) is created in the same folder as the exe on first launch.

---

## Project Structure

```
food-diary/
├── app.py                  # Flask app — routes, auth, API, DB
├── requirements.txt        # Python dependencies (flask only)
├── start.bat               # Windows launcher (runs from source)
├── build.bat               # Builds the standalone exe
├── food_diary.spec         # PyInstaller build config
├── templates/
│   ├── index.html          # Main diary UI
│   ├── login.html          # Sign-in page
│   ├── register.html       # Account creation (hidden URL)
│   └── report.html         # Printable report page
└── static/
    ├── sw.js               # Service worker (PWA offline support)
    └── icons/              # App icons (72px – 512px)
```

---

## API

All endpoints require an active session (login first).

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/entries?date=YYYY-MM-DD` | Get all entries for a date |
| `POST` | `/api/entries` | Add an entry |
| `PUT` | `/api/entries/<id>` | Edit an entry |
| `DELETE` | `/api/entries/<id>` | Delete an entry |
| `GET` | `/api/export?from=YYYY-MM-DD&to=YYYY-MM-DD` | Download CSV |

**POST / PUT body:**
```json
{
  "date": "2026-04-22",
  "meal": "breakfast",
  "food_name": "Oatmeal",
  "notes": "with blueberries"
}
```

Valid meal values: `breakfast`, `snack1`, `lunch`, `snack2`, `dinner`

---

## Database

SQLite, single file: `food_diary.db`

```sql
users (id, username, password_hash, created_at)
entries (id, user_id, date, meal, food_name, notes, created_at)
```

Passwords are hashed with Werkzeug's `pbkdf2:sha256`. The database file is excluded from this repository via `.gitignore` — it contains personal data and should never be committed.

---

## License

MIT
