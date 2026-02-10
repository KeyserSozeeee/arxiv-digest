import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any

DB_PATH = Path("arxiv_digest.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS summaries (
            paper_id TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            relevance REAL NOT NULL,
            novelty REAL NOT NULL,
            tldr TEXT NOT NULL,
            why TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def get_summary(paper_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    cur = conn.execute(
        "SELECT paper_id, model, relevance, novelty, tldr, why, created_at FROM summaries WHERE paper_id = ?",
        (paper_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "paper_id": row[0],
        "model": row[1],
        "relevance": row[2],
        "novelty": row[3],
        "tldr": row[4],
        "why": row[5],
        "created_at": row[6],
    }


def put_summary(
    paper_id: str,
    model: str,
    relevance: float,
    novelty: float,
    tldr: str,
    why: str,
    created_at: str,
) -> None:
    conn = _connect()
    conn.execute(
        """
        INSERT OR REPLACE INTO summaries
        (paper_id, model, relevance, novelty, tldr, why, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (paper_id, model, relevance, novelty, tldr, why, created_at),
    )
    conn.commit()
    conn.close()