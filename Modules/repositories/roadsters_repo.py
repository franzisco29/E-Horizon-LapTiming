from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from Modules.db import Database


@dataclass
class RoadsterRow:
    roadster_id: int
    team: str
    driver1_id: int
    driver2_id: int

    def display(self, d1_label: str, d2_label: str) -> str:
        return f"{d1_label}  +  {d2_label}   |   {self.team}"


class RoadstersRepo:
    def __init__(self, db: Database):
        self.db = db
        self._ensure()

    def _ensure(self) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS roadsters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team TEXT NOT NULL,
                    driver1_id INTEGER NOT NULL,
                    driver2_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            # evita duplicati invertiti (1,2) == (2,1)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS ux_roadsters_pair
                ON roadsters(
                    CASE WHEN driver1_id < driver2_id THEN driver1_id ELSE driver2_id END,
                    CASE WHEN driver1_id < driver2_id THEN driver2_id ELSE driver1_id END
                )
            """)
            conn.commit()

    def list_all(self) -> List[RoadsterRow]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT id, team, driver1_id, driver2_id FROM roadsters ORDER BY id DESC"
            ).fetchall()

        return [
            RoadsterRow(
                roadster_id=int(r["id"]),
                team=str(r["team"]),
                driver1_id=int(r["driver1_id"]),
                driver2_id=int(r["driver2_id"]),
            )
            for r in rows
        ]

    def upsert(self, roadster_id: int, team: str, driver1_id: int, driver2_id: int) -> int:
        a, b = sorted([driver1_id, driver2_id])

        with self.db.connect() as conn:
            if roadster_id > 0:
                conn.execute(
                    "UPDATE roadsters SET team=?, driver1_id=?, driver2_id=? WHERE id=?",
                    (team, a, b, roadster_id),
                )
                conn.commit()
                return roadster_id

            cur = conn.execute(
                "INSERT INTO roadsters(team, driver1_id, driver2_id) VALUES(?,?,?)",
                (team, a, b),
            )
            conn.commit()
            return int(cur.lastrowid)

    def delete_by_id(self, roadster_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM roadsters WHERE id=?", (roadster_id,))
            conn.commit()
