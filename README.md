# 🎧 DJHelper

Turn a **Spotify playlist** into a **harmonically-mixed Traktor Pro set** — on your own machine.

DJHelper imports a playlist, gets the audio for each track, analyzes **BPM, musical key (Camelot), and energy** locally, sequences the tracks into a smooth DJ set (harmonic mixing + BPM matching + an energy arc), and exports a **Traktor `.nml` collection with hot cues** plus an **`.m3u8` playlist**. An optional **local AI pass (Gemma via Ollama)** narrates the set and can re-order it.

It runs **locally** (a small web app at `http://localhost:8765`) so it can reach your files, your music, and your local AI — none of which a normal hosted website can do. The code lives on GitHub; you run it on your Mac.

---

## Why local-first?

| Feature | Needs to run on *your* machine |
|---|---|
| Download audio (yt-dlp) | ✅ filesystem + network |
| Analyze BPM / key / energy | ✅ reads the actual audio files |
| Write Traktor `.nml` / `.m3u8` | ✅ writes to your music folders |
| Local AI (Gemma) | ✅ talks to Ollama on `localhost` |

A public web link is sandboxed and can do none of these, so DJHelper ships as a one-command local app.

---

## Quick start

```bash
git clone <your-repo-url> DJHelper
cd DJHelper
cp .env.example .env          # then add your Spotify credentials
brew install ffmpeg           # required for audio extraction
./run.sh                      # first run sets up a venv + installs deps
```

Open **http://localhost:8765**.

### 1. Spotify credentials
1. Go to <https://developer.spotify.com/dashboard> → **Create app** (any name/redirect).
2. Copy the **Client ID** and **Client Secret** into `.env`.
   These use the *client-credentials* flow (no login) and read **public** playlists.

> Note: Spotify deprecated its audio-features/analysis API for new apps in late 2024, so DJHelper computes BPM/key/energy itself from the audio — which is more accurate for DJing anyway.

### 2. Local AI (optional)
```bash
# install Ollama from https://ollama.com, then:
ollama pull gemma2:2b      # light & fast
# or, if you have the RAM/VRAM:
ollama pull gemma2:9b
```
Set `OLLAMA_MODEL` in `.env`. If Ollama isn't running, DJHelper just uses the deterministic harmonic engine (which is excellent on its own).

---

## How it works

1. **Import** — paste a Spotify playlist URL. DJHelper pulls the track list.
2. **Download & analyze** — for each track it finds a matching file in your music folder, or downloads it with `yt-dlp` (toggleable), then analyzes it:
   - **BPM** via beat tracking (folded into a sane DJ range)
   - **Key** via Krumhansl-Schmuckler profiles → **Camelot** code
   - **Energy** from RMS loudness
   - **Mix-in cue** at the first downbeat, **Mix-out cue** N beats before the end
3. **Build the set** — greedy sequencing that balances:
   - harmonic compatibility (Camelot wheel),
   - BPM proximity (half/double-time aware),
   - an energy curve that rises to a peak then eases off.
   Tune the weights with the sliders; optionally let Gemma re-order and narrate.
4. **Export** — writes a Traktor `.nml` (tempo + Mix In/Out hot cues + an ordered playlist) and an `.m3u8`, into `data/exports/`.
   - In Traktor: **File ▸ Import Collection** → pick the `.nml`, or drag the `.m3u8` into a playlist.

---

## Harmonic mixing (Camelot)

Compatible transitions DJHelper favours, in order:
`same key` › `±1 same letter` › `relative major/minor` › `±2 (energy boost)`.
Anything else is flagged **risky** in the set view so you know to hand-mix it.

---

## Traktor paths on macOS

The `.nml` encodes file locations as `VOLUME` + `DIR` with `/:` separators.
Set **`TRAKTOR_VOLUME`** in `.env` to your boot drive's name (Finder sidebar — usually `Macintosh HD`). If imported tracks show as "missing" in Traktor, that value is the thing to fix.

---

## Project layout

```
backend/
  main.py        FastAPI app + serves the UI
  spotify.py     playlist import (spotipy, client-credentials)
  downloader.py  yt-dlp wrapper + local-file matching
  analysis.py    librosa BPM / key / energy / cues
  camelot.py     key → Camelot + harmonic compatibility
  sequencer.py   set-ordering algorithm
  traktor.py     .nml + .m3u8 generation
  ai.py          optional Gemma (Ollama) narrate / reorder
  jobs.py        background download+analyze with progress
  store.py       JSON library store
frontend/        single-page UI (Tailwind CDN + vanilla JS)
```

---

## ⚖️ Legal

DJHelper itself downloads nothing from a server we run — it orchestrates `yt-dlp`
**on your machine, under your control**. You are responsible for ensuring you
have the right to download and use any audio (e.g. you own it, it's licensed to
you, or local law permits it). This tool is for personal, lawful use.

## License
MIT — see [LICENSE](LICENSE).
