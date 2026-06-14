"""DJHelper API + static frontend (local-first, runs on your machine)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, config, jobs, sequencer, spotify, store, traktor

app = FastAPI(title="DJHelper")

FRONTEND = config.ROOT / "frontend"


# ---------- request models ----------
class PlaylistReq(BaseModel):
    url: str


class ProcessReq(BaseModel):
    download: bool = True
    ids: Optional[List[str]] = None


class SequenceReq(BaseModel):
    peak: float = 0.7
    harmonic: float = 0.5
    bpm: float = 0.35
    energy: float = 0.15
    use_ai: bool = False


class ExportReq(BaseModel):
    name: str = "DJHelper Set"
    ids: List[str]  # ordered track ids


# ---------- API ----------
@app.get("/api/health")
def health():
    return {
        "ok": True,
        "spotify_configured": bool(config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET),
        "ollama": ai.available(),
        "ollama_model": config.OLLAMA_MODEL,
        "music_dir": str(config.MUSIC_DIR),
        "export_dir": str(config.EXPORT_DIR),
    }


@app.get("/api/library")
def library():
    return {"tracks": store.all_tracks()}


@app.post("/api/playlist")
def import_playlist(req: PlaylistReq):
    try:
        tracks = spotify.fetch_playlist(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    for t in tracks:
        store.upsert(t)
    return {"imported": len(tracks), "tracks": tracks}


@app.post("/api/process")
def process(req: ProcessReq):
    ids = req.ids or [t["id"] for t in store.all_tracks()]
    if not ids:
        raise HTTPException(status_code=400, detail="Library is empty.")
    if not jobs.start(ids, do_download=req.download):
        raise HTTPException(status_code=409, detail="A job is already running.")
    return {"started": True, "count": len(ids)}


@app.get("/api/status")
def job_status():
    return jobs.status()


@app.post("/api/sequence")
def do_sequence(req: SequenceReq):
    tracks = [t for t in store.all_tracks() if t.get("status") == "analyzed"]
    if not tracks:
        raise HTTPException(status_code=400, detail="No analyzed tracks yet.")
    ordered = sequencer.sequence(
        tracks,
        weights={"harmonic": req.harmonic, "bpm": req.bpm, "energy": req.energy},
        peak=req.peak,
    )
    narrative = ""
    ai_used = False
    if req.use_ai:
        ids = ai.reorder(ordered)
        if ids:
            by_id = {t["id"]: t for t in ordered}
            ordered = [by_id[i] for i in ids]
            ai_used = True
        info = ai.describe_set(ordered)
        narrative = info.get("narrative", "")
    ordered = sequencer.annotate_transitions(ordered)
    return {"ordered": ordered, "narrative": narrative, "ai_used": ai_used}


@app.post("/api/export")
def export(req: ExportReq):
    by_id = {t["id"]: t for t in store.all_tracks()}
    ordered = [by_id[i] for i in req.ids if i in by_id]
    if not ordered:
        raise HTTPException(status_code=400, detail="No matching tracks to export.")
    nml = traktor.write_nml(ordered, req.name)
    m3u = traktor.write_m3u(ordered, req.name)
    return {
        "nml": str(nml), "m3u": str(m3u),
        "nml_name": nml.name, "m3u_name": m3u.name,
        "export_dir": str(config.EXPORT_DIR),
    }


@app.get("/api/download/{kind}/{filename}")
def download_export(kind: str, filename: str):
    f = config.EXPORT_DIR / filename
    if not f.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(f), filename=filename)


@app.delete("/api/library")
def clear_library():
    store.clear()
    return {"cleared": True}


# ---------- static frontend ----------
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")


def main():
    import uvicorn
    config.ensure_dirs()
    print("\n  DJHelper running at  http://localhost:8765\n")
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
