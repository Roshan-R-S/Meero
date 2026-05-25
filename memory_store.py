"""Simple SQLite-backed conversation memory store with minimal schema.
This provides a persistent fallback for conversation history.
"""
import sqlite3
import os
from typing import List, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "conversation.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        response TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return conn


def append(query: str, response: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO history (query, response) VALUES (?, ?)", (query, response))
    conn.commit()
    conn.close()


def last(n: int = 10) -> List[Tuple[str, str]]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT query, response FROM history ORDER BY id DESC LIMIT ?", (n,))
    rows = cur.fetchall()
    conn.close()
    # Return in chronological order
    return list(reversed(rows))
