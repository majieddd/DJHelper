"""Audio analysis: BPM, musical key (Krumhansl-Schmuckler), energy, mix cues.

Computed from the actual audio file with librosa, so it works regardless of how
the file was obtained and does not depend on Spotify's (now deprecated) audio
feature endpoints.
"""
from __future__ import annotations

from typing import Dict

from . import camelot, config

# Krumhansl-Schmuckler key profiles.
_MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def _corr(a, b) -> float:
    import numpy as np
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a - a.mean()
    b = b - b.mean()
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(a.dot(b) / denom) if denom else 0.0


def _detect_key(chroma):
    """Return (pitch_class, is_major) best matching the mean chroma vector."""
    import numpy as np
    mean = chroma.mean(axis=1)
    best = (0, True, -2.0)
    for pc in range(12):
        rotated = np.roll(mean, -pc)
        maj = _corr(rotated, _MAJOR_PROFILE)
        minr = _corr(rotated, _MINOR_PROFILE)
        if maj > best[2]:
            best = (pc, True, maj)
        if minr > best[2]:
            best = (pc, False, minr)
    return best[0], best[1]


def analyze_file(path: str) -> Dict:
    """Analyze an audio file. Returns dict of analysis fields.

    Raises on unreadable audio.
    """
    import librosa
    import numpy as np

    # Load mono. Cap to ~4 min for speed; key/energy/BPM are stable across it.
    y, sr = librosa.load(path, sr=22050, mono=True, duration=240)
    duration = librosa.get_duration(y=y, sr=sr)

    # --- BPM + beats ---
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    # fold extreme tempos into the typical DJ range
    while bpm and bpm < 70:
        bpm *= 2
    while bpm and bpm > 180:
        bpm /= 2
    beat_times = librosa.frames_to_time(beats, sr=sr)

    # --- Key ---
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    pc, is_major = _detect_key(chroma)

    # --- Energy ---
    # Pure loudness saturates (every mastered club track is loud), so blend
    # loudness with brightness (spectral centroid) and rhythmic density (onset
    # strength). The sequencer additionally normalises energy across the set.
    rms = librosa.feature.rms(y=y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    loud = float(np.clip(rms.mean() / 0.15, 0.0, 1.0))
    bright = float(np.clip(centroid.mean() / 5000.0, 0.0, 1.0))
    density = float(np.clip(onset.mean() / 3.0, 0.0, 1.0))
    energy = float(np.clip(0.5 * loud + 0.25 * bright + 0.25 * density, 0.0, 1.0))

    # --- Mix cues ---
    full_duration_ms = duration * 1000.0
    cue_in_ms = float(beat_times[0] * 1000.0) if len(beat_times) else 0.0
    if bpm > 0:
        ms_per_beat = 60000.0 / bpm
        cue_out_ms = max(0.0, full_duration_ms - config.MIX_OUT_BEATS * ms_per_beat)
    else:
        cue_out_ms = full_duration_ms

    return {
        "bpm": round(bpm, 2),
        "key_pitch": pc,
        "key_major": bool(is_major),
        "camelot": camelot.to_camelot(pc, is_major),
        "key_name": camelot.key_name(pc, is_major),
        "energy": round(energy, 3),
        "cue_in_ms": round(cue_in_ms, 1),
        "cue_out_ms": round(cue_out_ms, 1),
        "duration_ms": int(full_duration_ms),
        "status": "analyzed",
        "error": None,
    }
