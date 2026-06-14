"""Fetch playlist track metadata from Spotify.

PRIMARY path: scrape Spotify's public *embed* page, which exposes the full
track list (title / artist / duration) as JSON with NO API credentials and no
login. This makes DJHelper plug-and-play.

OPTIONAL fallback: if SPOTIFY_CLIENT_ID/SECRET are set, use the official API
(spotipy, client-credentials) -- useful for very large or edge-case playlists.

Either way we only ever read METADATA. BPM / key / energy are computed locally
from the downloaded audio (analysis.py), since Spotify deprecated its
audio-features endpoint for new apps in late 2024.
"""
from __future__ import annotations

import json
import re
from typing import List, Tuple

import requests

from . import config

_PLAYLIST_RE = re.compile(r"playlist[/:]([A-Za-z0-9]+)")
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def extract_playlist_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    m = _PLAYLIST_RE.search(url_or_id)
    if m:
        return m.group(1)
    return url_or_id.split("?")[0]


def _find(obj, key):
    """Depth-first search for the first value under `key`."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find(v, key)
            if r is not None:
                return r
    return None


def _clean(s: str) -> str:
    return (s or "").replace(" ", " ").strip()


def _empty_record(idx: int, tid: str) -> dict:
    return {
        "id": tid,
        "title": "",
        "artist": "",
        "album": "",
        "spotify_url": "",
        "duration_ms": 0,
        "file": None,
        "status": "pending",
        "error": None,
        "bpm": None,
        "key_pitch": None,
        "key_major": None,
        "camelot": None,
        "key_name": None,
        "energy": None,
        "cue_in_ms": None,
        "cue_out_ms": None,
    }


def _fetch_via_embed(pid: str) -> Tuple[List[dict], str]:
    url = f"https://open.spotify.com/embed/playlist/{pid}"
    r = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
    r.raise_for_status()
    m = _NEXT_DATA_RE.search(r.text)
    if not m:
        raise RuntimeError("Could not parse Spotify embed page (layout changed?).")
    data = json.loads(m.group(1))
    track_list = _find(data, "trackList")
    if not track_list:
        raise RuntimeError(
            "No tracks found. Is the playlist public? (Private playlists need "
            "Spotify API credentials in .env.)"
        )
    playlist_name = _clean(_find(data, "name") or "") or "Spotify Playlist"

    tracks: List[dict] = []
    for i, item in enumerate(track_list):
        uri = item.get("uri", "")
        tid = uri if uri else f"spotify:idx:{i}"
        rec = _empty_record(i, tid)
        rec["title"] = _clean(item.get("title")) or "Unknown"
        rec["artist"] = _clean(item.get("subtitle")) or "Unknown"
        rec["duration_ms"] = int(item.get("duration") or 0)
        if uri.startswith("spotify:track:"):
            rec["spotify_url"] = f"https://open.spotify.com/track/{uri.split(':')[-1]}"
        tracks.append(rec)
    return tracks, playlist_name


def _fetch_via_api(pid: str) -> Tuple[List[dict], str]:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    auth = SpotifyClientCredentials(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
    )
    sp = spotipy.Spotify(auth_manager=auth)
    name = "Spotify Playlist"
    try:
        name = sp.playlist(pid, fields="name").get("name", name)
    except Exception:
        pass
    tracks: List[dict] = []
    results = sp.playlist_items(pid, additional_types=("track",))
    while results:
        for item in results.get("items", []):
            t = item.get("track")
            if not t or t.get("type") != "track":
                continue
            tid = f"spotify:track:{t['id']}" if t.get("id") else f"spotify:idx:{len(tracks)}"
            rec = _empty_record(len(tracks), tid)
            rec["title"] = t.get("name", "Unknown")
            rec["artist"] = ", ".join(a["name"] for a in t.get("artists", [])) or "Unknown"
            rec["album"] = (t.get("album") or {}).get("name", "")
            rec["spotify_url"] = (t.get("external_urls") or {}).get("spotify", "")
            rec["duration_ms"] = t.get("duration_ms", 0)
            tracks.append(rec)
        results = sp.next(results) if results.get("next") else None
    return tracks, name


def fetch_playlist(url_or_id: str) -> Tuple[List[dict], str]:
    """Return (track records, playlist name). Tries the credential-free embed
    first; falls back to the API only if the embed fails AND creds are set."""
    pid = extract_playlist_id(url_or_id)
    try:
        return _fetch_via_embed(pid)
    except Exception as embed_err:
        if config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET:
            return _fetch_via_api(pid)
        raise RuntimeError(str(embed_err))
