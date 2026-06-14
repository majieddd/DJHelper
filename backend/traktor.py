"""Generate Traktor Pro collection (.nml) with cue points + an M3U playlist.

The NML carries, per track: tempo (BPM) and two hot cues -- a mix-in cue at the
first downbeat (HOTCUE 0) and a mix-out cue N beats before the end (HOTCUE 1).
Import it in Traktor via File > Import Collection, or drag the .nml's playlist.

Traktor on macOS encodes file locations as VOLUME + DIR + FILE where the path
separators are '/:'. Set TRAKTOR_VOLUME in .env to your boot drive's name.
"""
from __future__ import annotations

from pathlib import Path
from typing import List
from xml.sax.saxutils import quoteattr

from . import config


def _to_location(file_path: str):
    """Return (volume, dir, filename) in Traktor's '/:'-separated form."""
    p = Path(file_path).resolve()
    parts = p.parts[1:-1]  # drop leading '/' and the filename
    dir_str = "/:" + "/:".join(parts) + "/:" if parts else "/:"
    return config.TRAKTOR_VOLUME, dir_str, p.name


def _primary_key(file_path: str) -> str:
    vol, dir_str, name = _to_location(file_path)
    return f"{vol}{dir_str}{name}"


def _entry_xml(t: dict) -> str:
    file_path = t.get("file")
    if not file_path:
        return ""
    vol, dir_str, name = _to_location(file_path)
    bpm = t.get("bpm") or 0.0

    cues = []
    if t.get("cue_in_ms") is not None:
        cues.append(
            f'    <CUE_V2 NAME="Mix In" DISPL_ORDER="0" TYPE="0" '
            f'START="{float(t["cue_in_ms"]):.6f}" LEN="0.000000" REPEATS="-1" HOTCUE="0"></CUE_V2>'
        )
    if t.get("cue_out_ms") is not None:
        cues.append(
            f'    <CUE_V2 NAME="Mix Out" DISPL_ORDER="1" TYPE="0" '
            f'START="{float(t["cue_out_ms"]):.6f}" LEN="0.000000" REPEATS="-1" HOTCUE="1"></CUE_V2>'
        )
    cue_block = "\n".join(cues)

    title = quoteattr(t.get("title", "Unknown"))
    artist = quoteattr(t.get("artist", "Unknown"))
    album = quoteattr(t.get("album", ""))
    playtime = int((t.get("duration_ms") or 0) / 1000)

    return (
        f'  <ENTRY MODIFIED_DATE="2026/1/1" MODIFIED_TIME="0" TITLE={title} ARTIST={artist}>\n'
        f'    <LOCATION DIR={quoteattr(dir_str)} FILE={quoteattr(name)} '
        f'VOLUME={quoteattr(vol)} VOLUMEID={quoteattr(vol)}></LOCATION>\n'
        f'    <ALBUM TITLE={album}></ALBUM>\n'
        f'    <INFO PLAYTIME="{playtime}" KEY={quoteattr(t.get("key_name") or "")} '
        f'COMMENT={quoteattr("Camelot " + (t.get("camelot") or ""))}></INFO>\n'
        f'    <TEMPO BPM="{float(bpm):.6f}" BPM_QUALITY="100.000000"></TEMPO>\n'
        f'{cue_block}\n'
        f'  </ENTRY>'
    )


def write_nml(ordered: List[dict], name: str = "DJHelper Set") -> Path:
    config.ensure_dirs()
    have_files = [t for t in ordered if t.get("file")]

    entries = "\n".join(e for e in (_entry_xml(t) for t in have_files) if e)

    pl_entries = "\n".join(
        f'        <ENTRY><PRIMARYKEY TYPE="TRACK" KEY={quoteattr(_primary_key(t["file"]))}></PRIMARYKEY></ENTRY>'
        for t in have_files
    )

    nml = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<NML VERSION="19">
<HEAD COMPANY="www.native-instruments.com" PROGRAM="Traktor"></HEAD>
<MUSICFOLDERS></MUSICFOLDERS>
<COLLECTION ENTRIES="{len(have_files)}">
{entries}
</COLLECTION>
<PLAYLISTS>
  <NODE TYPE="FOLDER" NAME="$ROOT">
    <SUBNODES COUNT="1">
      <NODE TYPE="PLAYLIST" NAME={quoteattr(name)}>
        <PLAYLIST ENTRIES="{len(have_files)}" TYPE="LIST" UUID="djhelperset0000000000000000000000">
{pl_entries}
        </PLAYLIST>
      </NODE>
    </SUBNODES>
  </NODE>
</PLAYLISTS>
</NML>
'''
    out = config.EXPORT_DIR / f"{_safe(name)}.nml"
    out.write_text(nml, encoding="utf-8")
    return out


def write_m3u(ordered: List[dict], name: str = "DJHelper Set") -> Path:
    config.ensure_dirs()
    lines = ["#EXTM3U"]
    for t in ordered:
        if not t.get("file"):
            continue
        secs = int((t.get("duration_ms") or 0) / 1000)
        lines.append(f"#EXTINF:{secs},{t.get('artist','')} - {t.get('title','')}")
        lines.append(t["file"])
    out = config.EXPORT_DIR / f"{_safe(name)}.m3u8"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _safe(name: str) -> str:
    import re
    return re.sub(r"[^\w\- ]", "_", name).strip() or "set"
