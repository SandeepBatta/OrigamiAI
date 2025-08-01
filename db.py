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


def get_session_summaries(user_id: str) -> list[tuple[str, str, str]]:
    """
    Returns a list of (session_id, snippet, ts) sorted by newest‑first.
    snippet = a snippet of the first message.
    ts = timestamp of the first message.
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
        snippet = (content[:20] + "...") if len(content) > 20 else content
        summaries.append((session_id, snippet, ts))
    return summaries


def get_all_users_with_chats() -> list[tuple[str, int, str]]:
    """
    Returns a list of (user_id, message_count, last_activity) for all users with chat data.
    Sorted by last activity (newest first).
    """
    cur.execute(
        """
        SELECT user_id, COUNT(*) as message_count, MAX(ts) as last_activity
        FROM messages
        GROUP BY user_id
        ORDER BY last_activity DESC
        """
    )
    return cur.fetchall()


def get_user_chat_sessions(user_id: str) -> list[tuple[str, str, int, str]]:
    """
    Returns a list of (session_id, snippet, message_count, last_activity) for a specific user.
    Sorted by last activity (newest first).
    """
    cur.execute(
        """
        SELECT 
            session_id,
            (SELECT content FROM messages m2 WHERE m2.session_id = m.session_id AND m2.user_id = m.user_id ORDER BY ts LIMIT 1) as first_message,
            COUNT(*) as message_count,
            MAX(ts) as last_activity
        FROM messages m
        WHERE user_id = ?
        GROUP BY session_id
        ORDER BY last_activity DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    summaries = []
    for session_id, content, count, ts in rows:
        snippet = (
            (content[:30] + "...")
            if content and len(content) > 30
            else (content or "Empty session")
        )
        summaries.append((session_id, snippet, count, ts))
    return summaries


# User-specific analytics functions
def get_user_total_images_created(user_id: str) -> int:
    """Get total number of images created by AI for a specific user."""
    cur.execute(
        """
        SELECT COUNT(*) FROM messages 
        WHERE role = 'assistant' AND type != 'text' AND user_id = ?
        """,
        (user_id,),
    )
    return cur.fetchone()[0]


def get_user_images_created_over_time(user_id: str) -> list[tuple[str, int]]:
    """Get number of images created per day for a specific user."""
    cur.execute(
        """
        SELECT DATE(ts) as date, COUNT(*) as count
        FROM messages 
        WHERE role = 'assistant' AND type != 'text' AND user_id = ?
        GROUP BY DATE(ts)
        ORDER BY date
        """,
        (user_id,),
    )
    return cur.fetchall()


def get_user_activity_over_time(user_id: str) -> list[tuple[str, int]]:
    """Get user activity per day for a specific user (all messages)."""
    cur.execute(
        """
        SELECT DATE(ts) as date, COUNT(*) as message_count
        FROM messages
        WHERE user_id = ?
        GROUP BY DATE(ts)
        ORDER BY date
        """,
        (user_id,),
    )
    return cur.fetchall()


def get_user_messages_over_time(user_id: str) -> list[tuple[str, int]]:
    """Get only user messages per day (excluding AI responses)."""
    cur.execute(
        """
        SELECT DATE(ts) as date, COUNT(*) as user_message_count
        FROM messages
        WHERE user_id = ? AND role = 'user'
        GROUP BY DATE(ts)
        ORDER BY date
        """,
        (user_id,),
    )
    return cur.fetchall()


def get_user_message_distribution(user_id: str) -> list[tuple[str, int]]:
    """Get distribution of message types for a specific user."""
    cur.execute(
        """
        SELECT 
            CASE 
                WHEN role = 'user' THEN 'User Messages'
                WHEN role = 'assistant' AND type = 'text' THEN 'AI Text Responses'
                WHEN role = 'assistant' AND type != 'text' THEN 'AI Images'
                ELSE 'Other'
            END as message_type,
            COUNT(*) as count
        FROM messages
        WHERE user_id = ?
        GROUP BY message_type
        ORDER BY count DESC
        """,
        (user_id,),
    )
    return cur.fetchall()


def get_user_hourly_breakdown(user_id: str) -> list[tuple[int, int, int]]:
    """Get hourly breakdown of user messages vs AI responses."""
    cur.execute(
        """
        SELECT 
            CAST(strftime('%H', ts) AS INTEGER) as hour,
            SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
            SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as ai_responses
        FROM messages
        WHERE user_id = ?
        GROUP BY hour
        ORDER BY hour
        """,
        (user_id,),
    )
    return cur.fetchall()


def get_user_session_length_stats(user_id: str) -> list[tuple[str, int, int]]:
    """Get session statistics for a specific user: (session_id, message_count, duration_minutes)."""
    cur.execute(
        """
        SELECT 
            session_id,
            COUNT(*) as message_count,
            CAST((julianday(MAX(ts)) - julianday(MIN(ts))) * 24 * 60 AS INTEGER) as duration_minutes
        FROM messages
        WHERE user_id = ?
        GROUP BY session_id
        HAVING COUNT(*) > 1
        ORDER BY message_count DESC
        LIMIT 50
        """,
        (user_id,),
    )
    return cur.fetchall()


def get_user_total_messages(user_id: str) -> int:
    """Get total number of messages for a specific user."""
    cur.execute(
        """
        SELECT COUNT(*) FROM messages WHERE user_id = ?
        """,
        (user_id,),
    )
    return cur.fetchone()[0]


def get_user_total_sessions(user_id: str) -> int:
    """Get total number of sessions for a specific user."""
    cur.execute(
        """
        SELECT COUNT(DISTINCT session_id) FROM messages WHERE user_id = ?
        """,
        (user_id,),
    )
    return cur.fetchone()[0]


def get_user_last_activity(user_id: str) -> str:
    """Get last activity date for a specific user."""
    cur.execute(
        """
        SELECT MAX(ts) FROM messages WHERE user_id = ?
        """,
        (user_id,),
    )
    result = cur.fetchone()[0]
    return result if result else "Never"


def export_user_chat_data(user_id: str) -> list[dict]:
    """Export all chat data for a specific user."""
    cur.execute(
        """
        SELECT session_id, role, type, content, url, ts
        FROM messages
        WHERE user_id = ?
        ORDER BY ts
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    return [
        {
            "session_id": row[0],
            "role": row[1],
            "type": row[2],
            "content": row[3],
            "url": row[4],
            "timestamp": row[5],
        }
        for row in rows
    ]
