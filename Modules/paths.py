from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


REQUIRED_FOLDERS: List[str] = ["Data", "Results", "RAW", "Logs", "Settings", "Resources"]
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


def get_app_base_dir() -> Path:
    """
    Ritorna la cartella "base" dell'app da cui leggere le risorse.

    - In dev: cartella dove si trova questo file (o comunque il modulo corrente).
    - In exe PyInstaller: cartella di estrazione temporanea (sys._MEIPASS).
    - In exe "onedir": spesso coincide con la cartella dell'exe.
    """
    # PyInstaller onefile -> risorse estratte qui
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()

    # Eseguibile frozen non-PyInstaller o PyInstaller onedir: usa cartella dell'exe
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    # Dev: folder del file corrente
    return Path(__file__).resolve().parent


def sync_folder_contents(src: Path, dst: Path) -> bool:
    """
    Copia il CONTENUTO di src dentro dst (non crea dst/src, ma riempie dst).
    Ritorna True se ha copiato qualcosa.
    """
    if not src.exists() or not src.is_dir():
        return False

    dst.mkdir(parents=True, exist_ok=True)

    copied_any = False
    for item in src.iterdir():
        s = item
        d = dst / item.name
        if item.is_dir():
            shutil.copytree(s, d, dirs_exist_ok=True)
            copied_any = True
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            copied_any = True
    return copied_any


def create_required_folders(
    new_root: str | Path,
    *,
    old_root: Optional[str | Path] = None,
    force_creation: bool = False,
    root_path_change: bool = True,
    force_change: bool = False,
    delete_old: bool = False,
    copy_app_resources: bool = True,
    app_resources_subdir: str = "Resources",
) -> RootMigrationResult:
    """
    - Migra Data/Results/RAW/Logs/Settings/Resources da old_root -> new_root
    - Crea cartelle richieste
    - (Nuovo) Riempie new_root/Resources con le risorse della cartella app (main.py/.exe)

    copy_app_resources=True:
        copia da <app_base>/<app_resources_subdir> -> <new_root>/Resources
    """
    new_root_p = Path(new_root).expanduser().resolve()
    old_root_p = Path(old_root).expanduser().resolve() if old_root else None

    warnings: List[str] = []
    created_any = False
    migrated = False
    removed_old = False

    # Evita sottocartella (come VB)
    if old_root_p and not force_change and _is_subpath(new_root_p, old_root_p):
        warnings.append(
            "Il nuovo percorso non può essere una sottocartella del precedente (a meno di force_change=True)."
        )
        return RootMigrationResult(False, False, False, warnings)

    # Migrazione da old_root -> new_root
    if root_path_change and old_root_p and old_root_p != new_root_p and old_root_p.exists():
        for folder in REQUIRED_FOLDERS:
            src = old_root_p / folder
            if not src.exists():
                continue
            dst = new_root_p / folder
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            migrated = True

        # userData.ini
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

    # (Nuovo) Copia risorse "di app" dentro new_root/Resources
    if copy_app_resources:
        app_base = get_app_base_dir()
        src_res = app_base / app_resources_subdir
        dst_res = new_root_p / "Resources"

        copied = sync_folder_contents(src_res, dst_res)
        if not copied:
            warnings.append(
                f"Nessuna risorsa copiata: non trovo '{app_resources_subdir}' in '{app_base}'."
            )

    return RootMigrationResult(created_any, migrated, removed_old, warnings)