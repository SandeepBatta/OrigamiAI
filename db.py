import sqlite3
import os
from uuid import uuid4

# ensure folder exists
os.makedirs(os.path.dirname(__file__), exist_ok=True)
DB_PATH = os.path.join(os.path.dirname(__file__), "chat.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute(
    """
CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      TEXT,
    session_id   TEXT,
    role         TEXT,
    type         TEXT,
    content      TEXT,
    url          TEXT,
    ts           DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""
)
conn.commit()


def new_session(user_id: str) -> str:
    """Return a new session UUID (you may tie it to user_id if you like)."""
    return uuid4().hex


def save_message(user_id: str, session_id: str, msg: dict):
    """Persist a single message (text or image)."""
    cur.execute(
        """
        INSERT INTO messages(user_id, session_id, role, type, content, url)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            user_id,
            session_id,
            msg["role"],
            msg["type"],
            msg.get("content", ""),
            msg.get("url", ""),
        ),
    )
    conn.commit()


def load_messages(user_id: str, session_id: str) -> list[dict]:
    """Fetch all messages for this user & session, ordered chronologically."""
    cur.execute(
        """
        SELECT role, type, content, url
        FROM messages
        WHERE user_id=? AND session_id=?
        ORDER BY ts
    """,
        (user_id, session_id),
    )
    rows = cur.fetchall()
    return [{"role": r, "type": t, "content": c, "url": u} for r, t, c, u in rows]


def get_sessions(user_id: str) -> list[str]:
    """Return all distinct session_ids for this user, ordered by first message timestamp."""
    cur.execute(
        """
      SELECT DISTINCT session_id
      FROM messages
      WHERE user_id=?
      ORDER BY ts
    """,
        (user_id,),
    )
    return [row[0] for row in cur.fetchall()]


def get_session_summaries(user_id: str) -> list[tuple[str, str]]:
    """
    Returns a list of (session_id, title) sorted by newest‑first.
    Title = date of first message + a snippet of that first message.
    """
    cur.execute(
        """
      SELECT m.session_id, m.content, m.ts
      FROM messages m
      JOIN (
        SELECT session_id, MIN(ts) AS first_ts
        FROM messages
        WHERE user_id=?
        GROUP BY session_id
      ) sub
      ON m.session_id = sub.session_id AND m.ts = sub.first_ts
      ORDER BY sub.first_ts DESC
    """,
        (user_id,),
    )
    rows = cur.fetchall()
    summaries = []
    for session_id, content, ts in rows:
        date = ts.split(" ")[0]  # “YYYY‑MM‑DD”
        snippet = (content[:20] + "...") if len(content) > 20 else content
        title = f"{date} — {snippet}"
        summaries.append((session_id, snippet))
    return summaries
