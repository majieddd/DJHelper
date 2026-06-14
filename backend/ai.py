"""Optional local-AI pass via Ollama (Gemma). Falls back gracefully if Ollama
is not running. Produces a short, human-readable set narrative and an optional
re-ordering suggestion -- it never overrides the deterministic harmonic engine
unless you ask it to.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

import requests

from . import config


def available() -> bool:
    try:
        r = requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _tracklist_text(ordered: List[dict]) -> str:
    lines = []
    for i, t in enumerate(ordered, 1):
        lines.append(
            f"{i}. {t.get('artist','')} - {t.get('title','')} "
            f"[{t.get('camelot','?')}, {t.get('bpm','?')} BPM, energy {t.get('energy','?')}]"
        )
    return "\n".join(lines)


def describe_set(ordered: List[dict]) -> Dict:
    """Ask Gemma to narrate the set + flag weak transitions. Returns
    {available, narrative, model} ; narrative is '' if Ollama is down."""
    if not available():
        return {"available": False, "narrative": "", "model": config.OLLAMA_MODEL}

    prompt = (
        "You are an expert DJ. Below is a harmonically-sequenced set "
        "(Camelot key, BPM, energy 0-1). In 4-6 sentences, describe the arc of "
        "the set, name the natural peak, and flag any 1-2 transitions a DJ "
        "should hand-mix carefully. Be concrete and concise.\n\n"
        f"{_tracklist_text(ordered)}"
    )
    try:
        r = requests.post(
            f"{config.OLLAMA_HOST}/api/generate",
            json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return {
            "available": True,
            "narrative": r.json().get("response", "").strip(),
            "model": config.OLLAMA_MODEL,
        }
    except Exception as e:
        return {"available": False, "narrative": f"(AI error: {e})", "model": config.OLLAMA_MODEL}


def reorder(ordered: List[dict]) -> Optional[List[str]]:
    """Ask Gemma for an alternative ordering. Returns a list of track ids in the
    suggested order, or None if unavailable / unparseable."""
    if not available():
        return None
    indexed = [{"id": t["id"], "label": f"{t.get('artist','')} - {t.get('title','')}",
                "camelot": t.get("camelot"), "bpm": t.get("bpm"),
                "energy": t.get("energy")} for t in ordered]
    prompt = (
        "Reorder these tracks into the best DJ set: smooth harmonic (Camelot) "
        "transitions, gradual BPM changes, energy rising to a peak then easing. "
        "Reply with ONLY a JSON array of the 'id' values in your chosen order.\n\n"
        f"{json.dumps(indexed)}"
    )
    try:
        r = requests.post(
            f"{config.OLLAMA_HOST}/api/generate",
            json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False,
                  "format": "json"},
            timeout=120,
        )
        r.raise_for_status()
        data = json.loads(r.json().get("response", "[]"))
        if isinstance(data, dict):  # model sometimes wraps it, e.g. {"id": [...]}
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break
        valid = {t["id"] for t in ordered}
        # Take the model's order for the ids it actually returned (dedup, valid
        # only), then append any tracks it omitted in their algorithmic order.
        # This guarantees a full permutation even when a small model drops or
        # duplicates a few ids -- the AI still shapes the set, nothing is lost.
        seen = set()
        model_order = []
        for x in data:
            if isinstance(x, str) and x in valid and x not in seen:
                seen.add(x)
                model_order.append(x)
        if len(model_order) < max(2, len(ordered) // 2):
            return None  # too little usable signal -> keep the algorithmic order
        missing = [t["id"] for t in ordered if t["id"] not in seen]
        return model_order + missing
    except Exception:
        return None
