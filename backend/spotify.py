"""Fetch playlist track metadata from Spotify.

Uses the client-credentials flow (no user login) which can read PUBLIC
playlists. Spotify deprecated the audio-features / audio-analysis endpoints for
new apps in late 2024, so we deliberately do NOT rely on them -- BPM, key and
energy are computed locally from the downloaded audio (see analysis.py).
"""
from __future__ import annotations

import re
from typing import List

from . import config

_PLAYLIST_RE = re.compile(r"playlist[/:]([A-Za-z0-9]+)")


def extract_playlist_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    m = _PLAYLIST_RE.search(url_or_id)
    if m:
        return m.group(1)
    # assume it's already a bare id
    return url_or_id.split("?")[0]


def _client():
    if not config.SPOTIFY_CLIENT_ID or not config.SPOTIFY_CLIENT_SECRET:
        raise RuntimeError(
            "Spotify credentials missing. Set SPOTIFY_CLIENT_ID and "
            "SPOTIFY_CLIENT_SECRET in your .env (see README)."
        )
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    auth = SpotifyClientCredentials(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
    )
    return spotipy.Spotify(auth_manager=auth)


def fetch_playlist(url_or_id: str) -> List[dict]:
    """Return a list of track records (not yet downloaded/analyzed)."""
    sp = _client()
    pid = extract_playlist_id(url_or_id)
    tracks: List[dict] = []
    results = sp.playlist_items(pid, additional_types=("track",))
    while results:
        for item in results.get("items", []):
            t = item.get("track")
            if not t or t.get("type") != "track":
                continue
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            tracks.append({
                "id": f"spotify:track:{t['id']}" if t.get("id") else f"spotify:unknown:{len(tracks)}",
                "title": t.get("name", "Unknown"),
                "artist": artists or "Unknown",
                "album": (t.get("album") or {}).get("name", ""),
                "spotify_url": (t.get("external_urls") or {}).get("spotify", ""),
                "duration_ms": t.get("duration_ms", 0),
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
            })
        results = sp.next(results) if results.get("next") else None
    return tracks
