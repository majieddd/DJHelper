"""Download audio for a track using yt-dlp (searches YouTube by 'artist title').

IMPORTANT / LEGAL: this downloads audio from third-party sources. You are
responsible for having the rights to the material you download (e.g. you own it,
it is licensed for your use, or local law permits it). This runs entirely on
your machine and is not hosted as a public service.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from . import config


def _safe(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    return name.strip()[:120]


def download_track(track: dict) -> Path:
    """Download one track to MUSIC_DIR, return the audio file path.

    Raises RuntimeError on failure.
    """
    import yt_dlp

    config.ensure_dirs()
    query = f"{track.get('artist', '')} {track.get('title', '')}".strip()
    if not query:
        raise RuntimeError("Track has no artist/title to search for.")

    # Append a short token from the track id so two similarly-named tracks
    # (e.g. a song and its remix) can't collide on the same filename.
    tid = track.get("id", "")
    token = re.sub(r"\W", "", tid)[-6:] or "000000"
    stem = _safe(f"{track.get('artist','')} - {track.get('title','')}") + f" [{token}]"
    outtmpl = str(config.MUSIC_DIR / f"{stem}.%(ext)s")

    base_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
    }

    # YouTube returns HTTP 403 on the default web player client; the 'android'
    # client reliably yields a downloadable stream. Try a few clients in order.
    last_err = None
    for clients in (["android"], ["ios"], ["web_safari"], ["tv"]):
        opts = dict(base_opts)
        opts["extractor_args"] = {"youtube": {"player_client": clients}}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(query, download=True)
            last_err = None
            break
        except Exception as e:
            last_err = e
    if last_err is not None:
        raise RuntimeError(f"yt-dlp failed for '{query}': {last_err}")

    final = config.MUSIC_DIR / f"{stem}.mp3"
    if final.exists():
        return final
    # fall back to whatever extension landed
    for p in config.MUSIC_DIR.glob(f"{stem}.*"):
        return p
    raise RuntimeError(f"Download produced no file for '{query}'.")


def find_existing(track: dict, music_dir: Optional[Path] = None) -> Optional[Path]:
    """Match a track to an already-present audio file by fuzzy name."""
    music_dir = music_dir or config.MUSIC_DIR
    if not music_dir.exists():
        return None
    target = _safe(f"{track.get('artist','')} - {track.get('title','')}").lower()
    target_words = set(re.findall(r"\w+", target))
    best = None
    best_score = 0.0
    for p in music_dir.iterdir():
        if p.suffix.lower() not in (".mp3", ".wav", ".aiff", ".aif", ".flac", ".m4a"):
            continue
        words = set(re.findall(r"\w+", p.stem.lower()))
        if not words:
            continue
        score = len(target_words & words) / max(1, len(target_words | words))
        if score > best_score:
            best_score, best = score, p
    return best if best_score >= 0.5 else None
