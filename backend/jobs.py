"""Background job for downloading + analyzing a playlist, with progress polling."""
from __future__ import annotations

import threading
import traceback
from typing import Dict, List, Optional

from . import analysis, downloader, store

_lock = threading.Lock()
_job: Dict = {
    "running": False,
    "phase": "idle",       # idle | downloading | analyzing | done | error
    "total": 0,
    "done": 0,
    "current": "",
    "log": [],
    "error": None,
}


def status() -> Dict:
    with _lock:
        return dict(_job, log=list(_job["log"][-30:]))


def _log(msg: str) -> None:
    with _lock:
        _job["log"].append(msg)


def _set(**kw) -> None:
    with _lock:
        _job.update(kw)


def is_running() -> bool:
    with _lock:
        return _job["running"]


def _process(track_ids: List[str], do_download: bool) -> None:
    try:
        _set(running=True, phase="downloading", total=len(track_ids), done=0, error=None)
        for tid in track_ids:
            t = store.get(tid)
            if not t:
                continue
            _set(current=f"{t.get('artist','')} - {t.get('title','')}")

            # 1) ensure we have a file
            path = t.get("file")
            if not path:
                existing = downloader.find_existing(t)
                if existing:
                    path = str(existing)
                    store.update(tid, file=path, status="downloaded")
                    _log(f"matched local file: {existing.name}")
                elif do_download:
                    store.update(tid, status="downloading")
                    _log(f"downloading: {t.get('title','')}")
                    try:
                        p = downloader.download_track(t)
                        path = str(p)
                        store.update(tid, file=path, status="downloaded")
                    except Exception as e:
                        store.update(tid, status="error", error=str(e))
                        _log(f"download failed: {t.get('title','')} -> {e}")
                        with _lock:
                            _job["done"] += 1
                        continue
                else:
                    _log(f"no local file for: {t.get('title','')} (download disabled)")
                    with _lock:
                        _job["done"] += 1
                    continue

            # 2) analyze
            _set(phase="analyzing")
            try:
                result = analysis.analyze_file(path)
                store.update(tid, **result)
                _log(f"analyzed: {t.get('title','')} -> {result['camelot']} {result['bpm']} BPM")
            except Exception as e:
                store.update(tid, status="error", error=f"analysis: {e}")
                _log(f"analysis failed: {t.get('title','')} -> {e}")

            with _lock:
                _job["done"] += 1

        _set(running=False, phase="done", current="")
        _log("finished.")
    except Exception as e:
        _set(running=False, phase="error", error=str(e))
        _log("FATAL: " + traceback.format_exc())


def start(track_ids: List[str], do_download: bool = True) -> bool:
    if is_running():
        return False
    th = threading.Thread(target=_process, args=(track_ids, do_download), daemon=True)
    th.start()
    return True
