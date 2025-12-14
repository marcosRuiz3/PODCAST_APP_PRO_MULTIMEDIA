import sqlite3
from datetime import datetime


DB_PATH = "podcast.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS recordings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        filename TEXT UNIQUE,
        description TEXT,
        created_at TEXT,
        duration REAL
    )
    """)
    conn.commit()
    conn.close()


def add_recording(filename, title="", description="", duration=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO recordings (title, filename, description, created_at, duration) VALUES (?, ?, ?, ?, ?)",
        (title, filename, description, datetime.utcnow().isoformat(), duration)
    )
    conn.commit()
    conn.close()


def list_recordings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, filename, description, created_at, duration FROM recordings ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def update_recording_title(filename, new_title):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE recordings SET title=? WHERE filename=?", (new_title, filename))
    conn.commit()
    conn.close()


def update_recording_meta(filename, new_title, new_description):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE recordings SET title=?, description=? WHERE filename=?",
        (new_title, new_description, filename)
    )
    conn.commit()
    conn.close()
