from __future__ import annotations
from pathlib import Path
from datetime import datetime
from queue import Empty, Queue
import atexit
import threading

LOG_PATH = Path("logs") / "home_debug.log"
LOG_PATH.parent.mkdir(exist_ok=True)

_LOG_QUEUE: "Queue[str]" = Queue(maxsize=10000)
_STOP_EVENT = threading.Event()
_WRITER_THREAD: threading.Thread | None = None


def _flush_batch(batch: list[str]) -> None:
    if not batch:
        return
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.writelines(batch)


def _writer_loop() -> None:
    batch: list[str] = []
    while not _STOP_EVENT.is_set() or not _LOG_QUEUE.empty():
        try:
            line = _LOG_QUEUE.get(timeout=0.2)
            batch.append(line)
            if len(batch) >= 100:
                _flush_batch(batch)
                batch.clear()
        except Empty:
            if batch:
                _flush_batch(batch)
                batch.clear()

    if batch:
        _flush_batch(batch)


def _ensure_writer_started() -> None:
    global _WRITER_THREAD
    if _WRITER_THREAD is not None and _WRITER_THREAD.is_alive():
        return

    _STOP_EVENT.clear()
    _WRITER_THREAD = threading.Thread(target=_writer_loop, name="LOG-Writer", daemon=True)
    _WRITER_THREAD.start()


def shutdown_logger() -> None:
    _STOP_EVENT.set()
    if _WRITER_THREAD is not None and _WRITER_THREAD.is_alive():
        _WRITER_THREAD.join(timeout=1.5)


_ensure_writer_started()
atexit.register(shutdown_logger)

def log(msg: str, level: str = "INFO") -> None:
    lvl = level.upper()[:5].ljust(5)
    line = f"{datetime.now().isoformat(timespec='milliseconds')} | {lvl} | {msg}\n"
    # console
    print(line, end="", flush=True)
    # file (async buffered)
    try:
        _LOG_QUEUE.put_nowait(line)
    except Exception:
        # fallback sync if queue is saturated or unavailable
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)