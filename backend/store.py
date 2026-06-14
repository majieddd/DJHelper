"""Tiny JSON-file library store. One track = one dict, keyed by track id.

A track record looks like:
{
  "id": "spotify:track:..." or "local:<hash>",
  "title": str, "artist": str, "album": str,
  "spotify_url": str, "duration_ms": int,
  "file": str | None,            # absolute path to local audio once downloaded
  "status": "pending"|"downloading"|"downloaded"|"analyzed"|"error",
  "error": str | None,
  "bpm": float | None,
  "key_pitch": int | None, "key_major": bool | None,
  "camelot": str | None, "key_name": str | None,
  "energy": float | None,        # 0..1
  "cue_in_ms": float | None, "cue_out_ms": float | None,
}
"""
from __future__ import annotations

import json
import threading
from typing import Dict, List, Optional

from . import config

_lock = threading.RLock()
_cache: Optional[Dict[str, dict]] = None


def _load() -> Dict[str, dict]:
    global _cache
    if _cache is not None:
        return _cache
    config.ensure_dirs()
    if config.LIBRARY_FILE.exists():
        try:
            _cache = json.loads(config.LIBRARY_FILE.read_text())
        except Exception:
            _cache = {}
    else:
        _cache = {}
    return _cache


def _save() -> None:
    config.ensure_dirs()
    tmp = config.LIBRARY_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(_cache or {}, indent=2))
    tmp.replace(config.LIBRARY_FILE)


def all_tracks() -> List[dict]:
    with _lock:
        return list(_load().values())


def get(track_id: str) -> Optional[dict]:
    with _lock:
        return _load().get(track_id)


def upsert(track: dict) -> dict:
    with _lock:
        lib = _load()
        existing = lib.get(track["id"], {})
        existing.update(track)
        lib[track["id"]] = existing
        _save()
        return existing


def update(track_id: str, **fields) -> Optional[dict]:
    with _lock:
        lib = _load()
        if track_id not in lib:
            return None
        lib[track_id].update(fields)
        _save()
        return lib[track_id]


def remove(track_id: str) -> None:
    with _lock:
        lib = _load()
        lib.pop(track_id, None)
        _save()


def clear() -> None:
    with _lock:
        global _cache
        _cache = {}
        _save()
