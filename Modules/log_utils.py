from __future__ import annotations
from pathlib import Path
from datetime import datetime

LOG_PATH = Path("logs") / "home_debug.log"
LOG_PATH.parent.mkdir(exist_ok=True)

def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='milliseconds')} | {msg}\n"
    # console
    print(line, end="", flush=True)
    # file
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)