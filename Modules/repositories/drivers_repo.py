from __future__ import annotations

from typing import List, Optional
from Modules.db import Database

from dataclasses import dataclass

@dataclass
class DriverRow:
    driver_id: int
    name: str
    surname: str
    team: str
    transponder_id: int
    pro: bool
    race_number: int

    def display(self) -> str:
        return f"{self.name} {self.surname} | {self.team} | #{self.race_number} | Tras: {self.transponder_id}"


class DriversRepo:
    def __init__(self, db: Database):
        self.db = db

    def get_all(self) -> List[DriverRow]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT id, name, surname, team, transponder_id, race_number, pro "
                "FROM drivers ORDER BY id ASC"
            ).fetchall()

        return [
            DriverRow(
                driver_id=int(r["id"]),
                name=str(r["name"]),
                surname=str(r["surname"]),
                team=str(r["team"]),
                transponder_id=int(r["transponder_id"]),
                race_number=int(r["race_number"]),
                pro=bool(int(r["pro"])),
            )
            for r in rows
        ]

    def upsert(self, d: DriverRow) -> int:
        with self.db.connect() as conn:
            exists = None
            if d.driver_id > 0:
                exists = conn.execute("SELECT 1 FROM drivers WHERE id=?", (d.driver_id,)).fetchone()

            if exists:
                conn.execute(
                    "UPDATE drivers SET name=?, surname=?, team=?, transponder_id=?, race_number=?, pro=? WHERE id=?",
                    (d.name, d.surname, d.team, d.transponder_id, d.race_number, int(d.pro), d.driver_id),
                )
                conn.commit()
                return d.driver_id

            cur = conn.execute(
                "INSERT INTO drivers(name, surname, team, transponder_id, race_number, pro) VALUES(?,?,?,?,?,?)",
                (d.name, d.surname, d.team, d.transponder_id, d.race_number, int(d.pro)),
            )
            conn.commit()
            return int(cur.lastrowid)

    def delete_by_id(self, driver_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM drivers WHERE id=?", (driver_id,))
            conn.commit()

    def conflicts(self, transponder_id: int, race_number: int, exclude_id: Optional[int] = None) -> tuple[bool, bool]:
        with self.db.connect() as conn:
            if exclude_id is not None:
                t = conn.execute(
                    "SELECT 1 FROM drivers WHERE transponder_id=? AND id<>? LIMIT 1",
                    (transponder_id, exclude_id),
                ).fetchone()
                r = conn.execute(
                    "SELECT 1 FROM drivers WHERE race_number=? AND id<>? LIMIT 1",
                    (race_number, exclude_id),
                ).fetchone()
            else:
                t = conn.execute(
                    "SELECT 1 FROM drivers WHERE transponder_id=? LIMIT 1",
                    (transponder_id,),
                ).fetchone()
                r = conn.execute(
                    "SELECT 1 FROM drivers WHERE race_number=? LIMIT 1",
                    (race_number,),
                ).fetchone()

        return (t is not None, r is not None)
