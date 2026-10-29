"""SQLite persistence for user style feedback."""
import os
import sqlite3
from datetime import datetime, timezone

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BACKEND_DIR, "feedback.db")


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                style_shown TEXT NOT NULL,
                variant_shown TEXT NOT NULL,
                feedback_value TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                style_type TEXT DEFAULT 'hairstyle',
                current_rank INTEGER
            )
        """)
        # Safe, additive migration for databases created by the earlier version.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(feedback)")}
        if "style_type" not in columns:
            conn.execute("ALTER TABLE feedback ADD COLUMN style_type TEXT DEFAULT 'hairstyle'")
        if "current_rank" not in columns:
            conn.execute("ALTER TABLE feedback ADD COLUMN current_rank INTEGER")


def save_feedback(user_id, style_shown, variant_shown, feedback_value, style_type="hairstyle", current_rank=None):
    feedback_value = str(feedback_value).strip().lower()
    if feedback_value not in {"like", "dislike"}:
        raise ValueError("feedback_value must be 'like' or 'dislike'.")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as conn:
        cursor = conn.execute("""
            INSERT INTO feedback (user_id, style_shown, variant_shown, feedback_value, timestamp, style_type, current_rank)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(user_id), str(style_shown), str(variant_shown), feedback_value, timestamp, str(style_type), current_rank))
        record_id = cursor.lastrowid
    return {
        "id": record_id, "user_id": user_id, "style_shown": style_shown,
        "variant_shown": variant_shown, "feedback": feedback_value,
        "style_type": style_type, "current_rank": current_rank, "timestamp": timestamp
    }


def get_all_feedback():
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM feedback ORDER BY id").fetchall()
    return [dict(row) for row in rows]
