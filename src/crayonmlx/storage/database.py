"""Small SQLite repository; each operation owns its connection and transaction."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from crayonmlx.schemas import Settings


class Database:
    def __init__(self, root: Path):
        self.path = root / "crayonmlx.sqlite3"
        root.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS model_options (path TEXT PRIMARY KEY, enabled INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL,
                    request TEXT NOT NULL, source TEXT NOT NULL, output TEXT NOT NULL,
                    error TEXT, started_at TEXT, finished_at TEXT
                );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(jobs)")}
            if "execution" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN execution TEXT NOT NULL DEFAULT '{}'")
            # An interrupted render cannot be resumed without reloading its model.
            db.execute(
                "UPDATE jobs SET status='failed', error='Приложение было остановлено. Повторите генерацию.' WHERE status IN ('queued','running')"
            )
            db.execute(
                "INSERT OR IGNORE INTO settings VALUES (1, ?)",
                (
                    Settings(
                        models_dir=str(root / "models"), output_dir=str(root / "outputs")
                    ).model_dump_json(),
                ),
            )

    @contextmanager
    def connect(self):
        with sqlite3.connect(self.path, timeout=30) as db:
            db.row_factory = sqlite3.Row
            yield db

    def settings(self) -> Settings:
        with self.connect() as db:
            return Settings.model_validate_json(
                db.execute("SELECT body FROM settings WHERE id=1").fetchone()[0]
            )

    def save_settings(self, settings: Settings) -> None:
        with self.connect() as db:
            db.execute("UPDATE settings SET body=? WHERE id=1", (settings.model_dump_json(),))

    def add_job(self, job: dict) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO jobs (id, created_at, status, request, source, output) VALUES (:id,:created_at,:status,:request,:source,:output)",
                job,
            )

    def update_job(self, job_id: str, **changes) -> None:
        allowed = {"status", "error", "started_at", "finished_at", "execution"}
        if not changes or not changes.keys() <= allowed:
            raise ValueError("Invalid job update")
        with self.connect() as db:
            db.execute(
                f"UPDATE jobs SET {', '.join(f'{key}=?' for key in changes)} WHERE id=?",
                (*changes.values(), job_id),
            )

    def jobs(self, limit: int = 100, offset: int = 0) -> list[dict]:
        with self.connect() as db:
            return [
                self.decode(row)
                for row in db.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
                )
            ]

    def job(self, job_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return self.decode(row) if row else None

    @staticmethod
    def decode(row) -> dict:
        result = dict(row)
        result["request"] = json.loads(result["request"])
        result["execution"] = json.loads(result["execution"])
        return result

    def model_enabled(self, path: str) -> bool:
        with self.connect() as db:
            row = db.execute("SELECT enabled FROM model_options WHERE path=?", (path,)).fetchone()
            return bool(row[0]) if row else True

    def set_model_enabled(self, path: str, enabled: bool) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO model_options VALUES (?, ?) ON CONFLICT(path) DO UPDATE SET enabled=excluded.enabled",
                (path, int(enabled)),
            )

    def has_active_jobs(self) -> bool:
        with self.connect() as db:
            return (
                db.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running') LIMIT 1").fetchone()
                is not None
            )
