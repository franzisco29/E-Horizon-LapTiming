from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


REQUIRED_FOLDERS: List[str] = ["Drivers", "Racelists", "Roadsters", "Results", "RAW", "Logs"]
USER_FILE = "userData.ini"


@dataclass
class RootMigrationResult:
    created_any: bool
    migrated: bool
    removed_old: bool
    warnings: List[str]


def _is_subpath(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def create_required_folders(
    new_root: str | Path,
    *,
    old_root: Optional[str | Path] = None,
    force_creation: bool = False,
    root_path_change: bool = True,
    force_change: bool = False,
    delete_old: bool = False,
) -> RootMigrationResult:
    """
    Python equivalente di CreateRequiredFolders.

    - new_root: nuova root
    - old_root: root attuale (se vuoi migrare). Se None => non migra.
    - root_path_change: se True e old_root != new_root => migrazione
    - force_change: consente new_root dentro old_root
    - delete_old: elimina old_root dopo migrazione (no UI prompt)
    """
    new_root_p = Path(new_root).expanduser().resolve()
    old_root_p = Path(old_root).expanduser().resolve() if old_root else None

    warnings: List[str] = []
    created_any = False
    migrated = False
    removed_old = False

    # Evita sottocartella (come VB)
    if old_root_p and not force_change and _is_subpath(new_root_p, old_root_p):
        warnings.append("Il nuovo percorso non può essere una sottocartella del precedente (a meno di force_change=True).")
        return RootMigrationResult(False, False, False, warnings)

    # Migrazione
    if root_path_change and old_root_p and old_root_p != new_root_p and old_root_p.exists():
        # copia solo le cartelle richieste (e contenuti)
        for folder in REQUIRED_FOLDERS:
            src = old_root_p / folder
            if not src.exists():
                continue
            dst = new_root_p / folder
            dst.mkdir(parents=True, exist_ok=True)
            # copia contenuto
            shutil.copytree(src, dst, dirs_exist_ok=True)
            migrated = True

        # copia user file se presente
        src_user = old_root_p / USER_FILE
        if src_user.exists():
            new_root_p.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_user, new_root_p / USER_FILE)
            migrated = True

        if delete_old:
            shutil.rmtree(old_root_p, ignore_errors=True)
            removed_old = True

    # Crea cartelle richieste
    for folder in REQUIRED_FOLDERS:
        p = new_root_p / folder
        if force_creation or not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created_any = True

    return RootMigrationResult(created_any, migrated, removed_old, warnings)
