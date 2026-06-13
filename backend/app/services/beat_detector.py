"""Beat / tempo detection for music-video editing.

Self-contained DSP using numpy so it runs locally with no cloud dependency.
The approach (onset-envelope autocorrelation) is a pragmatic stand-in that can
be swapped for librosa/madmom by replacing `detect_beats` — the BeatGrid shape
it returns is what the rest of the studio depends on.
"""
from __future__ import annotations

import math

from ..models.project import BeatGrid

try:
    import numpy as np
except Exception:  # pragma: no cover - numpy is a hard dep in prod
    np = None  # type: ignore


def _onset_envelope(samples, sr: int, hop: int):
    """Spectral-flux-ish onset envelope from mono PCM via framed RMS deltas."""
    frames = []
    for i in range(0, len(samples) - hop, hop):
        frames.append(float(np.sqrt(np.mean(samples[i : i + hop] ** 2)) + 1e-9))
    env = np.asarray(frames)
    # Half-wave rectified first difference emphasises energy onsets.
    flux = np.diff(env, prepend=env[:1])
    flux[flux < 0] = 0
    if flux.max() > 0:
        flux = flux / flux.max()
    return flux


def detect_beats(samples, sr: int, media_id: str) -> BeatGrid:
    """Estimate BPM, beat times, downbeats and per-beat energy.

    `samples` is a 1-D float32 numpy array of mono PCM in [-1, 1].
    """
    if np is None:
        raise RuntimeError("numpy required for beat detection")

    hop = max(1, sr // 100)  # ~10 ms resolution
    env = _onset_envelope(samples, sr, hop)
    fps = sr / hop

    # Tempo via autocorrelation of the onset envelope within a sane BPM band.
    env_z = env - env.mean()
    ac = np.correlate(env_z, env_z, mode="full")[len(env_z) - 1 :]
    min_bpm, max_bpm = 60.0, 180.0
    lag_min = int(fps * 60.0 / max_bpm)
    lag_max = int(fps * 60.0 / min_bpm)
    lag_max = min(lag_max, len(ac) - 1)
    if lag_max <= lag_min:
        bpm = 120.0
    else:
        best_lag = lag_min + int(np.argmax(ac[lag_min:lag_max]))
        bpm = round(60.0 * fps / max(best_lag, 1), 1)

    # Lay a grid at the estimated tempo, phase-aligned to the strongest onset.
    period = 60.0 / bpm
    total_dur = len(samples) / sr
    if env.max() > 0:
        phase = (np.argmax(env) / fps) % period
    else:
        phase = 0.0

    beats: list[float] = []
    t = phase
    while t < total_dur:
        beats.append(round(t, 3))
        t += period

    # Per-beat energy = onset envelope sampled at each beat (0..1).
    energy: list[float] = []
    for b in beats:
        idx = min(int(b * fps), len(env) - 1)
        energy.append(round(float(env[idx]), 3))

    # Downbeats: every 4th beat, offset to the most energetic of the first four.
    if energy:
        start = int(np.argmax(energy[: min(4, len(energy))]))
    else:
        start = 0
    downbeats = list(range(start, len(beats), 4))

    confidence = float(np.clip(ac[best_lag] / (ac[0] + 1e-9), 0, 1)) if lag_max > lag_min else 0.3

    return BeatGrid(
        media_id=media_id,
        bpm=bpm,
        beats=beats,
        downbeats=downbeats,
        confidence=round(confidence, 3),
        energy=energy,
    )


def nearest_beat(grid: BeatGrid, t: float, downbeats_only: bool = False) -> float:
    """Snap an arbitrary time to the nearest beat (or downbeat)."""
    candidates = (
        [grid.beats[i] for i in grid.downbeats] if downbeats_only and grid.downbeats
        else grid.beats
    )
    if not candidates:
        return t
    return min(candidates, key=lambda b: abs(b - t))


def cut_density_for_energy(energy: float) -> int:
    """Suggested beats-per-cut: high energy → cut every beat, calm → every 4 bars."""
    if energy >= 0.75:
        return 1
    if energy >= 0.45:
        return 2
    if energy >= 0.2:
        return 4
    return 8
