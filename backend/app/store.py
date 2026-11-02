"""SQLite action store (stdlib sqlite3, single-writer transactions)."""
import json
import sqlite3
import time
import uuid
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  contributor TEXT NOT NULL,
  roster_email TEXT NOT NULL DEFAULT '',
  delivers_to TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  evidence_ids TEXT NOT NULL DEFAULT '[]',
  idempotency_key TEXT NOT NULL UNIQUE,
  error TEXT NOT NULL DEFAULT '',
  created_at REAL NOT NULL,
  sent_at REAL
);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_email_action(
        self, contributor: str, roster_email: str, delivers_to: str,
        subject: str, body: str, evidence_ids: list[str],
    ) -> dict:
        action_id = uuid.uuid4().hex[:12]
        key = uuid.uuid4().hex
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO actions (id, type, status, contributor, roster_email, delivers_to,"
                " subject, body, evidence_ids, idempotency_key, created_at)"
                " VALUES (?, 'email', 'pending', ?, ?, ?, ?, ?, ?, ?, ?)",
                (action_id, contributor, roster_email, delivers_to, subject, body,
                 json.dumps(evidence_ids), key, now),
            )
        return self.get(action_id)

    def get(self, action_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM actions WHERE id = ?", (action_id,)
            ).fetchone()
        return _row_to_dict(row) if row else None

    def get_by_key(self, idempotency_key: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM actions WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return _row_to_dict(row) if row else None

    def transition(self, action_id: str, expected: str, new: str, **fields) -> dict | None:
        """Atomic compare-and-set status change. Returns updated row or None."""
        sets = ", ".join(["status = ?"] + [f"{k} = ?" for k in fields])
        vals: list = [new, *fields.values(), action_id, expected]
        cols = ", ".join(["status"] + list(fields.keys()))
        _ = cols
        with self._conn() as conn:
            cur = conn.execute(
                f"UPDATE actions SET {sets} WHERE id = ? AND status = ?",
                vals,
            )
            if cur.rowcount != 1:
                return None
            row = conn.execute(
                "SELECT * FROM actions WHERE id = ?", (action_id,)
            ).fetchone()
        return _row_to_dict(row) if row else None

    def sends_in_last_hour(self) -> int:
        cutoff = time.time() - 3600
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM actions WHERE type='email'"
                " AND status IN ('sent','outbox_saved') AND sent_at > ?",
                (cutoff,),
            ).fetchone()
        return int(row["n"]) if row else 0

    def list_recent(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM actions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["evidence_ids"] = json.loads(d.get("evidence_ids") or "[]")
    except ValueError:
        d["evidence_ids"] = []
    return d
