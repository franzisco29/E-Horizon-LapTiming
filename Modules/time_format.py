from __future__ import annotations

from datetime import timedelta


def fmt_mm_ss_mmm(t: timedelta) -> str:
    """Formato 'mm:ss.fff' (VB: mm\\:ss\\.fff)."""
    if t is None:
        return "00:00.000"
    total_ms = int(t.total_seconds() * 1000)
    if total_ms < 0:
        total_ms = 0
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    m = (total_s // 60) % 60
    return f"{m:02d}:{s:02d}.{ms:03d}"


def fmt_ss_mmm(t: timedelta) -> str:
    """Formato 'ss.fff' (VB: ss\\.fff)."""
    if t is None:
        return "00.000"
    total_ms = int(t.total_seconds() * 1000)
    if total_ms <= 0:
        return "00.000"
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    return f"{s:02d}.{ms:03d}"
