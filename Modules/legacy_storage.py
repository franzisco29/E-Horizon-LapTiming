from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from Classes.driver import Driver
from Classes.race_list import RaceList
from Classes.roadster import Roadster


# ---------- Drivers ----------
def read_drivers(root: str | Path, driver_file_name: str = "drivers.txt") -> List[Driver]:
    root = Path(root)
    folder = root / "Drivers"
    folder.mkdir(parents=True, exist_ok=True)

    file_path = folder / driver_file_name
    if not file_path.exists():
        file_path.write_text("", encoding="utf-8")
        return []

    drivers: List[Driver] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split("|")
        try:
            driver_id = int(fields[0])
            name = fields[1]
            surname = fields[2]
            team = fields[3]
            number = int(fields[4])
            pro = fields[5].strip().lower() in ("true", "1", "yes")
            rnum = int(fields[6])
            drivers.append(Driver(driver_id, name, surname, number, team, pro, rnum))
        except Exception:
            # se vuoi: log in Logs/
            continue

    return drivers


def write_driver(root: str | Path, driver: Driver, driver_file_name: str = "drivers.txt") -> None:
    root = Path(root)
    folder = root / "Drivers"
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / driver_file_name
    with file_path.open("a", encoding="utf-8", newline="") as f:
        f.write(driver.to_file())


def rewrite_drivers(root: str | Path, drivers: List[Driver], driver_file_name: str = "drivers.txt") -> None:
    root = Path(root)
    folder = root / "Drivers"
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / driver_file_name
    file_path.write_text("", encoding="utf-8")
    with file_path.open("a", encoding="utf-8", newline="") as f:
        for d in drivers:
            f.write(d.to_file())


# ---------- Roadsters ----------
def read_roadsters(root: str | Path, drivers: List[Driver], roadster_file_name: str = "roadsters.txt") -> List[Roadster]:
    root = Path(root)
    folder = root / "Roadsters"
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / roadster_file_name

    if not file_path.exists():
        file_path.write_text("", encoding="utf-8")
        return []

    by_id = {d.driver_id: d for d in drivers}

    roadsters: List[Roadster] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split("|")
        try:
            id1 = int(fields[1])
            id2 = int(fields[2])
            fdriver = by_id.get(id1)
            sdriver = by_id.get(id2)
            if fdriver and sdriver:
                roadsters.append(Roadster(fdriver, sdriver))
        except Exception:
            continue

    return roadsters


def write_roadster(root: str | Path, roadster: Roadster, roadster_file_name: str = "roadsters.txt") -> None:
    root = Path(root)
    folder = root / "Roadsters"
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / roadster_file_name
    with file_path.open("a", encoding="utf-8", newline="") as f:
        f.write(roadster.to_file())


# ---------- RaceLists ----------
def read_race_list(
    root: str | Path,
    filename: str,
    *,
    endurance: bool,
    all_drivers: List[Driver],
) -> Optional[RaceList]:
    """
    VB: readListDrivers(filename, endurance, allDrivers)
    Nota: qui filename è già il nome del file dentro Racelists/
    """
    root = Path(root)
    folder = root / "Racelists"
    file_path = folder / filename
    if not file_path.exists():
        return None

    by_id = {d.driver_id: d for d in all_drivers}

    drivers: List[Driver] = []
    roadsters: List[Roadster] = []

    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split("|")

        try:
            if endurance:
                # team|id1|id2
                id1 = int(fields[1])
                id2 = int(fields[2])
                fdriver = by_id.get(id1)
                sdriver = by_id.get(id2)
                if fdriver and sdriver:
                    roadsters.append(Roadster(fdriver, sdriver))
            else:
                # driver_id|name|surname|team|number|pro|rnum
                driver_id = int(fields[0])
                name = fields[1]
                surname = fields[2]
                team = fields[3]
                number = int(fields[4])
                pro = fields[5].strip().lower() in ("true", "1", "yes")
                rnum = int(fields[6])
                drivers.append(Driver(driver_id, name, surname, number, team, pro, rnum))
        except Exception:
            continue

    if endurance:
        return RaceList(name=filename, roadsters=roadsters)
    return RaceList(name=filename, drivers=drivers)


def write_race_list(
    root: str | Path,
    race_list: RaceList,
    *,
    endurance_ext: str = ".endracelist",
    normal_ext: str = ".racelist",
) -> Path:
    """
    VB: writeList(raceList)
    """
    root = Path(root)
    folder = root / "Racelists"
    folder.mkdir(parents=True, exist_ok=True)

    out_name = race_list.get_file_name(endurance_ext=endurance_ext, normal_ext=normal_ext)
    file_path = folder / out_name
    file_path.write_text(race_list.to_file(), encoding="utf-8")
    return file_path


def find_lists(root: str | Path, *, endurance_list: bool, endurance_ext: str, normal_ext: str) -> List[Path]:
    """
    VB: findList(enduranceList)
    Cerca *_RaceList{ext} dentro root (tutte le subdir)
    """
    root = Path(root)
    ext = endurance_ext if endurance_list else normal_ext
    pattern = f"*_RaceList{ext}"
    return list(root.rglob(pattern))
