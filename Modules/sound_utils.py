"""Audio helpers for start-sequence tones on Windows.

Uses winsound.PlaySound with in-memory WAV data so the audio goes through
the actual sound card (WASAPI/DirectSound) instead of the PC speaker buzzer
used by winsound.Beep.
"""
from __future__ import annotations

import math
import struct
import threading

import winsound

from Modules.log_utils import log

# ---------------------------------------------------------------------------
# WAV generation
# ---------------------------------------------------------------------------

_SAMPLE_RATE = 44100


def _make_wav(freq_hz: int, duration_ms: int, volume: float = 0.7) -> bytes:
    """Return mono 16-bit PCM WAV bytes for a pure tone with short fade."""
    n = int(_SAMPLE_RATE * duration_ms / 1000)
    fade = min(int(_SAMPLE_RATE * 0.008), n // 4)  # 8 ms fade-in/out
    tw = 2.0 * math.pi * freq_hz / _SAMPLE_RATE
    pcm = bytearray(n * 2)
    for i in range(n):
        amp = volume
        if i < fade:
            amp *= i / fade
        elif i > n - fade:
            amp *= (n - i) / fade
        v = max(-32768, min(32767, int(32767 * amp * math.sin(tw * i))))
        struct.pack_into("<h", pcm, i * 2, v)
    data_size = len(pcm)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, _SAMPLE_RATE, _SAMPLE_RATE * 2, 2, 16,
        b"data", data_size,
    )
    return bytes(header) + bytes(pcm)


# Pre-built tones (computed once at import time)
_WAV_DO: bytes = _make_wav(262, 200)    # C4 ~DO, 200 ms
_WAV_SOL: bytes = _make_wav(392, 2000)  # G4 ~SOL, 2 s


# ---------------------------------------------------------------------------
# Playback helpers
# ---------------------------------------------------------------------------

def _play(wav: bytes) -> None:
    """Play WAV bytes synchronously via the audio card (blocking)."""
    try:
        winsound.PlaySound(wav, winsound.SND_MEMORY)
    except Exception as ex:
        log(f"[SUONO] Riproduzione audio fallita: {ex}", level="WARN")


def _play_async(wav: bytes) -> None:
    """Play WAV bytes on a daemon thread (non-blocking)."""
    threading.Thread(target=_play, args=(wav,), daemon=True, name="AudioTone").start()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def beep_do() -> None:
    """DO (C4 ~262 Hz) short beep for each light step S1-S5."""
    log("[SUONO] beep_do", level="DEBUG")
    _play_async(_WAV_DO)


def beep_lights_out() -> None:
    """SOL (G4 ~392 Hz) 2s tone for manual lights out."""
    log("[SUONO] beep_lights_out", level="DEBUG")
    _play_async(_WAV_SOL)
