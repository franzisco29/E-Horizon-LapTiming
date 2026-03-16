from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from Modules.db import Database


@dataclass
class CircuitRow:
    circuit_id: int
    name: str
    location: str
    track_length_m: float
    sector1_m: float
    sector2_m: float
    sector3_m: float
    notes: str

    def display(self) -> str:
        loc = f" | {self.location}" if self.location else ""
        return f"{self.name}{loc} | {self.track_length_m:.1f} m"


class CircuitsRepo:
    def __init__(self, db: Database):
        self.db = db
        self._ensure()

    def _ensure(self) -> None:
        with self.db.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS circuits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    location TEXT NOT NULL DEFAULT '',
                    track_length_m REAL NOT NULL,
                    sector1_m REAL NOT NULL,
                    sector2_m REAL NOT NULL,
                    sector3_m REAL NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TRIGGER IF NOT EXISTS circuits_updated_at
                AFTER UPDATE ON circuits
                FOR EACH ROW
                BEGIN
                  UPDATE circuits SET updated_at = datetime('now') WHERE id = OLD.id;
                END;
                """
            )
            conn.commit()

    def get_all(self) -> List[CircuitRow]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, location, track_length_m, sector1_m, sector2_m, sector3_m, notes
                FROM circuits
                ORDER BY name COLLATE NOCASE ASC
                """
            ).fetchall()

        return [
            CircuitRow(
                circuit_id=int(r["id"]),
                name=str(r["name"]),
                location=str(r["location"] or ""),
                track_length_m=float(r["track_length_m"]),
                sector1_m=float(r["sector1_m"]),
                sector2_m=float(r["sector2_m"]),
                sector3_m=float(r["sector3_m"]),
                notes=str(r["notes"] or ""),
            )
            for r in rows
        ]

    def upsert(self, row: CircuitRow) -> int:
        with self.db.connect() as conn:
            exists = None
            if row.circuit_id > 0:
                exists = conn.execute("SELECT 1 FROM circuits WHERE id=?", (row.circuit_id,)).fetchone()

            if exists:
                conn.execute(
                    """
                    UPDATE circuits
                    SET name=?, location=?, track_length_m=?, sector1_m=?, sector2_m=?, sector3_m=?, notes=?
                    WHERE id=?
                    """,
                    (
                        row.name,
                        row.location,
                        float(row.track_length_m),
                        float(row.sector1_m),
                        float(row.sector2_m),
                        float(row.sector3_m),
                        row.notes,
                        row.circuit_id,
                    ),
                )
                conn.commit()
                return int(row.circuit_id)

            cur = conn.execute(
                """
                INSERT INTO circuits(name, location, track_length_m, sector1_m, sector2_m, sector3_m, notes)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    row.name,
                    row.location,
                    float(row.track_length_m),
                    float(row.sector1_m),
                    float(row.sector2_m),
                    float(row.sector3_m),
                    row.notes,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def delete_by_id(self, circuit_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM circuits WHERE id=?", (int(circuit_id),))
            conn.commit()

    def conflicts(self, name: str, exclude_id: Optional[int] = None) -> bool:
        name = (name or "").strip()
        if not name:
            return False

        with self.db.connect() as conn:
            if exclude_id is not None:
                row = conn.execute(
                    "SELECT 1 FROM circuits WHERE lower(name)=lower(?) AND id<>? LIMIT 1",
                    (name, int(exclude_id)),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT 1 FROM circuits WHERE lower(name)=lower(?) LIMIT 1",
                    (name,),
                ).fetchone()

        return row is not None
