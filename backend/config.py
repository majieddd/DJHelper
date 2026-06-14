"""Configuration loaded from environment / .env file."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Project root (parent of backend/)
ROOT = Path(__file__).resolve().parent.parent

# Where downloaded audio + the library database live.
DATA_DIR = Path(os.getenv("DJHELPER_DATA_DIR", ROOT / "data")).expanduser()
MUSIC_DIR = Path(os.getenv("DJHELPER_MUSIC_DIR", DATA_DIR / "music")).expanduser()
EXPORT_DIR = Path(os.getenv("DJHELPER_EXPORT_DIR", DATA_DIR / "exports")).expanduser()
LIBRARY_FILE = DATA_DIR / "library.json"

# Spotify API credentials (client-credentials flow; public playlists only).
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

# Traktor: the macOS volume name Traktor uses in its collection paths.
# Find yours in Finder (the name of your boot drive), usually "Macintosh HD".
TRAKTOR_VOLUME = os.getenv("TRAKTOR_VOLUME", "Macintosh HD")

# Ollama (optional local AI). Model: gemma2:2b / gemma2:9b / gemma3:12b etc.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")

# How many beats before the end of a track to place the "mix-out" hot cue.
MIX_OUT_BEATS = int(os.getenv("DJHELPER_MIX_OUT_BEATS", "32"))


def ensure_dirs() -> None:
    for d in (DATA_DIR, MUSIC_DIR, EXPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)
