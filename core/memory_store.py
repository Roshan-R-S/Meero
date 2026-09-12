import os
import sqlite3
import threading
from typing import List, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "conversation.db")
DB_PATH = os.path.abspath(DB_PATH)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

_thread_local = threading.local()
_initialized_dbs = set()
_init_lock = threading.Lock()

_SCHEMA_SQL = (
    """CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL DEFAULT 'default',
        query TEXT,
        response TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS memory_summary (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        summary TEXT NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE INDEX IF NOT EXISTS idx_history_id ON history(id)""",
    """CREATE INDEX IF NOT EXISTS idx_history_session_id ON history(session_id)""",
)


def _get_conn():
    """Return a per-thread reusable connection.

    Reuses connections via threading.local() as long as DB_PATH matches,
    and runs the schema DDL once per distinct database file path.
    """
    conn = getattr(_thread_local, "conn", None)
    cached_path = getattr(_thread_local, "db_path", None)
    if conn is not None and cached_path == DB_PATH:
        try:
            conn.execute("SELECT 1")
            return conn
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)

    with _init_lock:
        if DB_PATH not in _initialized_dbs:
            for stmt in _SCHEMA_SQL:
                conn.execute(stmt)
            # Migrate older databases that lack the session_id column.
            try:
                conn.execute("SELECT session_id FROM history LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE history ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default'")
            conn.commit()
            _initialized_dbs.add(DB_PATH)

    _thread_local.conn = conn
    _thread_local.db_path = DB_PATH
    return conn


def append(query: str, response: str, max_interactions: int | None = None, summarizer=None):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO history (query, response) VALUES (?, ?)", (query, response))
    conn.commit()
    if max_interactions is not None:
        _prune_conn(conn, max_interactions=max_interactions, summarizer=summarizer)


def last(n: int = 10) -> List[Tuple[str, str]]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT query, response FROM history ORDER BY id DESC LIMIT ?", (n,))
    rows = cur.fetchall()
    return list(reversed(rows))


def get_summary() -> str:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT summary FROM memory_summary WHERE id = 1")
    row = cur.fetchone()
    return row[0] if row else ""


def update_summary(summary: str, conn=None) -> None:
    owns_conn = conn is None
    conn = conn or _get_conn()
    conn.execute(
        """INSERT INTO memory_summary (id, summary, updated_at)
           VALUES (1, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(id) DO UPDATE SET
             summary = excluded.summary,
             updated_at = CURRENT_TIMESTAMP""",
        (summary,),
    )
    conn.commit()


def summarize_turns(
    turns: List[Tuple[str, str]],
    existing_summary: str = "",
    max_chars: int = 1200,
) -> str:
    """Create a compact local summary without calling an external model.

    Uses sentence-boundary truncation instead of naive character slicing to
    avoid cutting context mid-sentence.
    """
    fragments = [existing_summary.strip()] if existing_summary.strip() else []
    for query, response in turns:
        fragments.append(f"User: {query} | Meero: {response}")
    summary = " ".join(fragments)
    if len(summary) <= max_chars:
        return summary
    # Take a slightly wider window and find the first sentence boundary.
    truncated = summary[-(max_chars + 100):]
    for sep in (". ", "! ", "? ", "| "):
        idx = truncated.find(sep)
        if idx != -1 and idx < 100:
            return truncated[idx + len(sep):]
    return truncated[-max_chars:].lstrip()


def prune(max_interactions: int = 20, summarizer=None):
    conn = _get_conn()
    return _prune_conn(conn, max_interactions=max_interactions, summarizer=summarizer)


def _prune_conn(conn, max_interactions: int = 20, summarizer=None):
    if max_interactions < 1:
        raise ValueError("max_interactions must be at least 1")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM history")
    count = cur.fetchone()[0]
    overflow = count - max_interactions
    if overflow <= 0:
        return 0

    cur.execute("SELECT id, query, response FROM history ORDER BY id ASC LIMIT ?", (overflow,))
    rows = cur.fetchall()
    turns = [(query, response) for _row_id, query, response in rows]
    existing = get_summary_from_conn(conn)
    summary_fn = summarizer or summarize_turns
    new_summary = summary_fn(turns, existing)
    update_summary(new_summary, conn=conn)

    row_ids = [row_id for row_id, _query, _response in rows]
    cur.executemany("DELETE FROM history WHERE id = ?", [(row_id,) for row_id in row_ids])
    conn.commit()
    return len(row_ids)


def get_summary_from_conn(conn) -> str:
    cur = conn.cursor()
    cur.execute("SELECT summary FROM memory_summary WHERE id = 1")
    row = cur.fetchone()
    return row[0] if row else ""


def clear():
    conn = _get_conn()
    conn.execute("DELETE FROM history")
    conn.execute("DELETE FROM memory_summary")
    conn.commit()


def export(limit: int | None = None, offset: int = 0) -> dict:
    conn = _get_conn()
    cur = conn.cursor()
    if limit is not None:
        cur.execute(
            "SELECT id, query, response, ts FROM history ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, max(0, offset)),
        )
    else:
        cur.execute("SELECT id, query, response, ts FROM history ORDER BY id ASC")
    rows = cur.fetchall()
    history = [{"id": r[0], "query": r[1], "response": r[2], "ts": r[3]} for r in rows]
    summary = get_summary_from_conn(conn)
    return {"history": history, "summary": summary}
