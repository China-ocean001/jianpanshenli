"""
SQLite persistence layer for Keyboard Forest.
All reads/writes happen on the main thread only.
"""

import sqlite3
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from config import DB_PATH, ALL_KEYS
from key_tree import KeyTree

_ISO_FMT = "%Y-%m-%dT%H:%M:%S.%f"
_DATE_FMT = "%Y-%m-%d"


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime(_ISO_FMT) if dt else None


def _from_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, _ISO_FMT)
    except ValueError:
        return datetime.fromisoformat(s)


class Database:
    def __init__(self, path: str = DB_PATH):
        self._conn = sqlite3.connect(path, check_same_thread=True)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS key_trees (
                key_name         TEXT PRIMARY KEY,
                stage            INTEGER NOT NULL DEFAULT 0,
                experience       REAL    NOT NULL DEFAULT 0.0,
                health           REAL    NOT NULL DEFAULT 1.0,
                total_presses    INTEGER NOT NULL DEFAULT 0,
                last_used        TEXT,
                custom_name      TEXT    NOT NULL DEFAULT '',
                trees_grown      INTEGER NOT NULL DEFAULT 0,
                was_dead         INTEGER NOT NULL DEFAULT 0,
                permanent_xp_boost INTEGER NOT NULL DEFAULT 0,
                skin_id          TEXT    NOT NULL DEFAULT '',
                created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS daily_stats (
                key_name    TEXT NOT NULL,
                date        TEXT NOT NULL,
                press_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (key_name, date)
            );

            CREATE TABLE IF NOT EXISTS health_history (
                key_name    TEXT NOT NULL,
                date        TEXT NOT NULL,
                health      REAL NOT NULL,
                stage       INTEGER NOT NULL,
                PRIMARY KEY (key_name, date)
            );

            CREATE TABLE IF NOT EXISTS achievements (
                id          TEXT PRIMARY KEY,
                unlocked_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_stats (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        self._conn.commit()
        self._migrate()

    def _migrate(self):
        """Apply schema migrations for existing databases."""
        migrations = [
            "ALTER TABLE key_trees ADD COLUMN trees_grown INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE key_trees ADD COLUMN was_dead INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE key_trees ADD COLUMN permanent_xp_boost INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE key_trees ADD COLUMN skin_id TEXT NOT NULL DEFAULT ''",
        ]
        for sql in migrations:
            try:
                self._conn.execute(sql)
                self._conn.commit()
            except Exception:
                pass  # column already exists

    # ── Load ───────────────────────────────────────────────────────────────

    def load_all_trees(self) -> Dict[str, KeyTree]:
        rows = {r["key_name"]: r for r in self._conn.execute("SELECT * FROM key_trees")}
        today_str = date.today().strftime(_DATE_FMT)
        today_counts = {
            r["key_name"]: r["press_count"]
            for r in self._conn.execute(
                "SELECT key_name, press_count FROM daily_stats WHERE date = ?",
                (today_str,),
            )
        }

        trees: Dict[str, KeyTree] = {}
        for key_name in ALL_KEYS:
            if key_name in rows:
                r = rows[key_name]
                trees[key_name] = KeyTree(
                    key_name=key_name,
                    stage=r["stage"],
                    experience=r["experience"],
                    health=r["health"],
                    total_presses=r["total_presses"],
                    last_used=_from_iso(r["last_used"]),
                    custom_name=r["custom_name"] or "",
                    today_presses=today_counts.get(key_name, 0),
                    trees_grown=r["trees_grown"],
                    was_dead=bool(r["was_dead"]),
                    permanent_xp_boost=bool(r["permanent_xp_boost"]),
                    skin_id=r["skin_id"] or "",
                )
            else:
                trees[key_name] = KeyTree(key_name=key_name)
        return trees

    def load_weekly_counts(self) -> Dict[str, int]:
        """Returns total presses per key over the last 7 days."""
        rows = self._conn.execute("""
            SELECT key_name, SUM(press_count) AS total
            FROM daily_stats
            WHERE date >= date('now', '-7 days')
            GROUP BY key_name
        """)
        return {r["key_name"]: r["total"] for r in rows}

    # ── Save ───────────────────────────────────────────────────────────────

    def save_all_trees(self, trees: Dict[str, KeyTree]):
        today_str = date.today().strftime(_DATE_FMT)
        tree_rows = []
        daily_rows = []
        for kt in trees.values():
            tree_rows.append((
                kt.key_name, kt.stage, kt.experience, kt.health,
                kt.total_presses, _to_iso(kt.last_used), kt.custom_name,
                kt.trees_grown, int(kt.was_dead), int(kt.permanent_xp_boost),
                kt.skin_id,
            ))
            if kt.today_presses > 0:
                daily_rows.append((kt.key_name, today_str, kt.today_presses))

        self._conn.executemany("""
            INSERT INTO key_trees (key_name, stage, experience, health,
                                   total_presses, last_used, custom_name,
                                   trees_grown, was_dead, permanent_xp_boost, skin_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(key_name) DO UPDATE SET
                stage              = excluded.stage,
                experience         = excluded.experience,
                health             = excluded.health,
                total_presses      = excluded.total_presses,
                last_used          = excluded.last_used,
                custom_name        = excluded.custom_name,
                trees_grown        = excluded.trees_grown,
                was_dead           = excluded.was_dead,
                permanent_xp_boost = excluded.permanent_xp_boost,
                skin_id            = excluded.skin_id
        """, tree_rows)

        if daily_rows:
            self._conn.executemany("""
                INSERT INTO daily_stats (key_name, date, press_count)
                VALUES (?,?,?)
                ON CONFLICT(key_name, date) DO UPDATE SET
                    press_count = excluded.press_count
            """, daily_rows)

        # Health history snapshot (daily)
        health_rows = [
            (kt.key_name, today_str, kt.health, kt.stage)
            for kt in trees.values() if kt.stage > 0
        ]
        if health_rows:
            self._conn.executemany("""
                INSERT INTO health_history (key_name, date, health, stage)
                VALUES (?,?,?,?)
                ON CONFLICT(key_name, date) DO UPDATE SET
                    health = excluded.health,
                    stage  = excluded.stage
            """, health_rows)

        self._conn.commit()

    def update_custom_name(self, key_name: str, name: str):
        self._conn.execute(
            "UPDATE key_trees SET custom_name = ? WHERE key_name = ?",
            (name, key_name),
        )
        self._conn.commit()

    # ── Statistics queries ─────────────────────────────────────────────────

    def get_key_period_stats(self, key_name: str, days: int = 30) -> List[Tuple[str, int]]:
        """Daily press counts for one key over last N days. Returns [(date, count)]."""
        rows = self._conn.execute("""
            SELECT date, press_count FROM daily_stats
            WHERE key_name = ? AND date >= date('now', ? )
            ORDER BY date ASC
        """, (key_name, f'-{days} days'))
        return [(r["date"], r["press_count"]) for r in rows]

    def get_health_history(self, key_name: str, days: int = 30) -> List[Tuple[str, float, int]]:
        """Health snapshots for one key. Returns [(date, health, stage)]."""
        rows = self._conn.execute("""
            SELECT date, health, stage FROM health_history
            WHERE key_name = ? AND date >= date('now', ?)
            ORDER BY date ASC
        """, (key_name, f'-{days} days'))
        return [(r["date"], r["health"], r["stage"]) for r in rows]

    def get_top_keys(self, n: int = 10, period_days: int = 7) -> List[Tuple[str, int]]:
        """Top N most-pressed keys over last period_days days."""
        rows = self._conn.execute("""
            SELECT key_name, SUM(press_count) AS total
            FROM daily_stats
            WHERE date >= date('now', ?)
            GROUP BY key_name
            ORDER BY total DESC
            LIMIT ?
        """, (f'-{period_days} days', n))
        return [(r["key_name"], r["total"]) for r in rows]

    def get_endangered_keys(self, n: int = 10) -> List[Tuple[str, float, int]]:
        """Keys with lowest health that are alive (stage>0, health>0). Returns [(key_name, health, stage)]."""
        rows = self._conn.execute("""
            SELECT key_name, health, stage FROM key_trees
            WHERE stage > 0 AND health > 0
            ORDER BY health ASC
            LIMIT ?
        """, (n,))
        return [(r["key_name"], r["health"], r["stage"]) for r in rows]

    def get_forest_summary(self) -> dict:
        """Aggregate forest stats from key_trees and daily_stats."""
        rows = list(self._conn.execute("SELECT stage, health FROM key_trees"))
        healthy = sick = dead = unplanted = 0
        for r in rows:
            if r["stage"] == 0:
                unplanted += 1
            elif r["health"] <= 0:
                dead += 1
            elif r["health"] < 0.5:
                sick += 1
            else:
                healthy += 1
        # Total presses today
        today_str = date.today().strftime(_DATE_FMT)
        res = self._conn.execute(
            "SELECT SUM(press_count) as t FROM daily_stats WHERE date = ?",
            (today_str,)
        ).fetchone()
        today_total = res["t"] or 0
        res2 = self._conn.execute("SELECT SUM(total_presses) as t FROM key_trees").fetchone()
        total_all = res2["t"] or 0
        return {
            "healthy": healthy, "sick": sick, "dead": dead, "unplanted": unplanted,
            "today_total": today_total, "total_all": total_all,
        }

    def get_monthly_stats(self, key_name: str) -> List[Tuple[str, int]]:
        """Monthly press totals for one key over last 12 months. Returns [(YYYY-MM, count)]."""
        rows = self._conn.execute("""
            SELECT strftime('%Y-%m', date) as month, SUM(press_count) as total
            FROM daily_stats
            WHERE key_name = ? AND date >= date('now', '-365 days')
            GROUP BY month ORDER BY month ASC
        """, (key_name,))
        return [(r["month"], r["total"]) for r in rows]

    def close(self):
        self._conn.close()

    # ── Achievements ───────────────────────────────────────────────────────

    def load_achievements(self) -> List[Tuple[str, str]]:
        """Returns [(id, unlocked_at)] for all unlocked achievements."""
        rows = self._conn.execute("SELECT id, unlocked_at FROM achievements")
        return [(r["id"], r["unlocked_at"]) for r in rows]

    def save_achievement(self, ach_id: str, unlocked_at: str):
        self._conn.execute(
            "INSERT OR IGNORE INTO achievements (id, unlocked_at) VALUES (?,?)",
            (ach_id, unlocked_at),
        )
        self._conn.commit()

    def get_app_stat(self, key: str, default: str = "0") -> str:
        row = self._conn.execute(
            "SELECT value FROM app_stats WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_app_stat(self, key: str, value: str):
        self._conn.execute(
            "INSERT INTO app_stats (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()

    def clear_all_data(self):
        """Wipe all user data. Cannot be undone."""
        self._conn.executescript("""
            DELETE FROM key_trees;
            DELETE FROM daily_stats;
            DELETE FROM health_history;
            DELETE FROM achievements;
            DELETE FROM app_stats;
        """)
        self._conn.commit()
