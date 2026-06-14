"""Order analyzed tracks into a DJ set.

Greedy nearest-neighbour over a transition score combining:
  - harmonic compatibility (Camelot wheel)
  - BPM proximity (smaller jump = smoother)
  - energy-curve fit (gentle rise to a peak, then come down)

This is deterministic and mirrors how DJs actually sequence sets. The optional
Gemma pass (ai.py) can re-rank on top of this.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from . import camelot


def _bpm_score(a: Optional[float], b: Optional[float]) -> float:
    if not a or not b:
        return 0.4
    diff = abs(a - b)
    # half/double-time mixing is fine
    diff = min(diff, abs(a - b / 2), abs(a - b * 2))
    if diff <= 1:
        return 1.0
    if diff >= 16:
        return 0.0
    return max(0.0, 1.0 - diff / 16.0)


def _energy_target(position: float, peak: float = 0.7) -> float:
    """Desired energy at fractional set position (0..1): rise to `peak`, then fall."""
    if position <= peak:
        return 0.35 + 0.65 * (position / peak)  # 0.35 -> 1.0
    return 1.0 - 0.5 * ((position - peak) / (1 - peak))  # 1.0 -> 0.5


def transition_score(a: dict, b: dict) -> float:
    harm = camelot.compatibility(a.get("camelot"), b.get("camelot"))
    bpm = _bpm_score(a.get("bpm"), b.get("bpm"))
    return 0.55 * harm + 0.45 * bpm


def sequence(
    tracks: List[dict],
    weights: Optional[Dict[str, float]] = None,
    peak: float = 0.7,
) -> List[dict]:
    """Return tracks reordered for mixing. Only analyzed tracks are sequenced;
    the rest are appended at the end untouched."""
    w = {"harmonic": 0.5, "bpm": 0.35, "energy": 0.15}
    if weights:
        w.update(weights)

    pool = [t for t in tracks if t.get("camelot") and t.get("bpm")]
    leftover = [t for t in tracks if not (t.get("camelot") and t.get("bpm"))]
    if not pool:
        return tracks

    # Start with the lowest-energy track (a natural set opener).
    pool_sorted = sorted(pool, key=lambda t: t.get("energy") or 0.5)
    current = pool_sorted[0]
    ordered = [current]
    remaining = [t for t in pool if t["id"] != current["id"]]

    while remaining:
        pos = len(ordered) / max(1, len(pool) - 1)
        e_target = _energy_target(pos, peak)
        best, best_score = None, -1.0
        for cand in remaining:
            harm = camelot.compatibility(current.get("camelot"), cand.get("camelot"))
            bpm = _bpm_score(current.get("bpm"), cand.get("bpm"))
            efit = 1.0 - abs((cand.get("energy") or 0.5) - e_target)
            score = w["harmonic"] * harm + w["bpm"] * bpm + w["energy"] * efit
            if score > best_score:
                best, best_score = cand, score
        ordered.append(best)
        remaining = [t for t in remaining if t["id"] != best["id"]]
        current = best

    return ordered + leftover


def annotate_transitions(ordered: List[dict]) -> List[dict]:
    """Attach per-track transition notes (to the NEXT track) for the UI."""
    out = []
    for i, t in enumerate(ordered):
        note = dict(t)
        if i + 1 < len(ordered):
            nxt = ordered[i + 1]
            harm = camelot.compatibility(t.get("camelot"), nxt.get("camelot"))
            label = (
                "perfect" if harm >= 1.0 else
                "smooth" if harm >= 0.85 else
                "energy boost" if harm >= 0.55 else
                "risky"
            )
            bpm_a, bpm_b = t.get("bpm"), nxt.get("bpm")
            bpm_delta = round(bpm_b - bpm_a, 1) if bpm_a and bpm_b else None
            note["transition"] = {
                "to": nxt.get("title"),
                "harmonic": label,
                "score": round(harm, 2),
                "bpm_delta": bpm_delta,
            }
        else:
            note["transition"] = None
        out.append(note)
    return out
