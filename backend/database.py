import os
import json
import time
import uuid
import sqlite3

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "halluciguard.db"))


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Database:
    """
    Thin storage layer for scan records.

    - If SUPABASE_URL and SUPABASE_KEY are set, reads/writes go to a Supabase
      Postgres table called "scans" (see supabase_schema.sql).
    - Otherwise, falls back to a local SQLite file so the project runs with
      zero external setup.
    """

    def __init__(self):
        self._use_supabase = USE_SUPABASE
        if self._use_supabase:
            from supabase import create_client
            self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
        else:
            self._init_sqlite()

    def backend_name(self) -> str:
        return "supabase" if self._use_supabase else "sqlite"

    # ---------- SQLite path ----------
    def _init_sqlite(self):
        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                response TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    # ---------- Public API ----------
    def insert_scan(self, question: str, response: str, result: dict) -> dict:
        record_id = str(uuid.uuid4())
        created_at = _now_iso()

        if self._use_supabase:
            row = {
                "id": record_id,
                "question": question,
                "response": response,
                "result": result,
                "created_at": created_at,
            }
            self._client.table("scans").insert(row).execute()
            return row

        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute(
            "INSERT INTO scans (id, question, response, result, created_at) VALUES (?, ?, ?, ?, ?)",
            (record_id, question, response, json.dumps(result), created_at),
        )
        conn.commit()
        conn.close()
        return {"id": record_id, "created_at": created_at}

    def list_scans(self, limit: int = 50) -> list:
        if self._use_supabase:
            res = (
                self._client.table("scans")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []

        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM scans ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()

        return [
            {
                "id": r["id"],
                "question": r["question"],
                "response": r["response"],
                "result": json.loads(r["result"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def clear_scans(self) -> None:
        if self._use_supabase:
            self._client.table("scans").delete().neq("id", "").execute()
            return

        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute("DELETE FROM scans")
        conn.commit()
        conn.close()

    def benchmark(self) -> dict:
        scans = self.list_scans(limit=1000)
        n = len(scans)
        if n == 0:
            return {"total_scans": 0, "avg_risk": 0, "avg_trust": 0, "hallucination_rate": 0}

        avg_risk = round(sum(s["result"].get("hallucination_risk", 0) for s in scans) / n)
        avg_trust = round(sum(s["result"].get("trust_score", 0) for s in scans) / n)
        flagged = sum(
            1 for s in scans if "hallucination" in (s["result"].get("verdict", "") or "").lower()
        )
        rate = round((flagged / n) * 100)

        return {
            "total_scans": n,
            "avg_risk": avg_risk,
            "avg_trust": avg_trust,
            "hallucination_rate": rate,
        }
