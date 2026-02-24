# Modules/repositories/racelists_repo.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from Modules.db import Database


@dataclass
class RaceListRow:
    list_id: int
    name: str
    is_endurance: bool

    def display(self) -> str:
        tag = "END" if self.is_endurance else "STD"
        return f"{self.name}   [{tag}]"


class RaceListsRepo:
    """
    Tabelle:
      - racelists: meta
      - racelist_drivers: items per liste standard (driver_id)
      - racelist_roadsters: items per liste endurance (roadster_id)
    """

    def __init__(self, db: Database):
        self.db = db
        self._ensure()

    def _ensure(self) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS racelists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    is_endurance INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS ux_racelists_name_type
                ON racelists(name, is_endurance)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS racelist_drivers (
                    list_id INTEGER NOT NULL,
                    pos INTEGER NOT NULL,
                    driver_id INTEGER NOT NULL,
                    PRIMARY KEY(list_id, driver_id),
                    FOREIGN KEY(list_id) REFERENCES racelists(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS racelist_roadsters (
                    list_id INTEGER NOT NULL,
                    pos INTEGER NOT NULL,
                    roadster_id INTEGER NOT NULL,
                    PRIMARY KEY(list_id, roadster_id),
                    FOREIGN KEY(list_id) REFERENCES racelists(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    # ---------- Lists ----------
    def list_all(self) -> List[RaceListRow]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT id, name, is_endurance FROM racelists ORDER BY id DESC"
            ).fetchall()

        return [
            RaceListRow(
                list_id=int(r["id"]),
                name=str(r["name"]),
                is_endurance=bool(int(r["is_endurance"])),
            )
            for r in rows
        ]

    def get(self, list_id: int) -> Optional[RaceListRow]:
        with self.db.connect() as conn:
            r = conn.execute(
                "SELECT id, name, is_endurance FROM racelists WHERE id=?",
                (int(list_id),),
            ).fetchone()
        if not r:
            return None
        return RaceListRow(list_id=int(r["id"]), name=str(r["name"]), is_endurance=bool(int(r["is_endurance"])))

    def delete_by_id(self, list_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM racelists WHERE id=?", (int(list_id),))
            conn.commit()

    # ---------- Items ----------
    def get_driver_ids(self, list_id: int) -> List[int]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT driver_id FROM racelist_drivers WHERE list_id=? ORDER BY pos ASC",
                (int(list_id),),
            ).fetchall()
        return [int(r["driver_id"]) for r in rows]

    def get_roadster_ids(self, list_id: int) -> List[int]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT roadster_id FROM racelist_roadsters WHERE list_id=? ORDER BY pos ASC",
                (int(list_id),),
            ).fetchall()
        return [int(r["roadster_id"]) for r in rows]

    def upsert_list(
        self,
        *,
        list_id: int,
        name: str,
        is_endurance: bool,
        item_ids: List[int],
    ) -> int:
        """
        - Se list_id > 0: update meta + riscrive items
        - Se list_id = 0: insert + items
        """
        name = (name or "").strip()
        if not name:
            raise ValueError("RaceList name is required.")

        with self.db.connect() as conn:
            if list_id > 0:
                conn.execute(
                    "UPDATE racelists SET name=?, is_endurance=? WHERE id=?",
                    (name, 1 if is_endurance else 0, int(list_id)),
                )
                new_id = int(list_id)
            else:
                cur = conn.execute(
                    "INSERT INTO racelists(name, is_endurance) VALUES(?,?)",
                    (name, 1 if is_endurance else 0),
                )
                new_id = int(cur.lastrowid)

            # clear + rewrite items
            conn.execute("DELETE FROM racelist_drivers WHERE list_id=?", (new_id,))
            conn.execute("DELETE FROM racelist_roadsters WHERE list_id=?", (new_id,))

            if is_endurance:
                for pos, rid in enumerate(item_ids, start=1):
                    conn.execute(
                        "INSERT INTO racelist_roadsters(list_id, pos, roadster_id) VALUES(?,?,?)",
                        (new_id, pos, int(rid)),
                    )
            else:
                for pos, did in enumerate(item_ids, start=1):
                    conn.execute(
                        "INSERT INTO racelist_drivers(list_id, pos, driver_id) VALUES(?,?,?)",
                        (new_id, pos, int(did)),
                    )

            conn.commit()
            return new_id