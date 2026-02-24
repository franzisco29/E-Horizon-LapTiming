from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, List, Tuple


@dataclass(frozen=True)
class Database:
    path: Path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn


def db_path_from_root(root_path: str | Path, filename: str = "ehorizon.db") -> Path:
    root = Path(root_path+"/Data")
    root.mkdir(parents=True, exist_ok=True)
    return (root / filename).resolve()


# -------------------------
# Meta helpers
# -------------------------
def _ensure_meta(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)


def get_meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    _ensure_meta(conn)
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row["value"])


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    _ensure_meta(conn)
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


# -------------------------
# Migrations
# -------------------------
def _migration_001(conn: sqlite3.Connection) -> None:
    # v1: drivers + trigger updated_at
    conn.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS drivers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          surname TEXT NOT NULL,
          team TEXT NOT NULL,
          transponder_id INTEGER NOT NULL UNIQUE,
          race_number INTEGER NOT NULL UNIQUE,
          pro INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TRIGGER IF NOT EXISTS drivers_updated_at
        AFTER UPDATE ON drivers
        FOR EACH ROW
        BEGIN
          UPDATE drivers SET updated_at = datetime('now') WHERE id = OLD.id;
        END;
    """)


# Lista migrazioni in ordine (versione, funzione)
MIGRATIONS: List[Tuple[int, Callable[[sqlite3.Connection], None]]] = [
    (1, _migration_001),
]


def init_db(db: Database) -> int:
    """
    Inizializza DB e applica tutte le migrazioni mancanti.
    Ritorna la schema_version finale.
    """
    db.path.parent.mkdir(parents=True, exist_ok=True)

    with db.connect() as conn:
        _ensure_meta(conn)

        current = get_meta(conn, "schema_version")
        current_version = int(current) if current and current.isdigit() else 0

        # Applica migrazioni mancanti
        for version, fn in MIGRATIONS:
            if version > current_version:
                conn.execute("BEGIN")
                try:
                    fn(conn)
                    set_meta(conn, "schema_version", str(version))
                    conn.commit()
                    current_version = version
                except Exception:
                    conn.rollback()
                    raise

        return current_version
    
def reset_database(db: Database) -> int:
    """
    ⚠ DEV ONLY.
    Cancella completamente il file database e lo ricrea applicando tutte le migrazioni.
    Ritorna la schema_version finale.
    """

    db_path = Path(db.path)

    # Se esiste, rimuovilo
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception as e:
            raise RuntimeError(f"Unable to delete database file: {e}")

    # Ricrea da zero
    return init_db(db)