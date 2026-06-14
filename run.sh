#!/usr/bin/env bash
# DJHelper launcher: sets up a venv on first run, then starts the app.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "→ Creating virtual environment…"
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  echo "→ Installing dependencies (this can take a few minutes the first time)…"
  ./.venv/bin/pip install -r requirements.txt
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "→ Created .env — add your Spotify credentials, then re-run."
fi

# ffmpeg is needed by yt-dlp to extract mp3.
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "⚠  ffmpeg not found. Install it with:  brew install ffmpeg"
fi

echo "→ Starting DJHelper…"
exec ./.venv/bin/python -m backend.main
