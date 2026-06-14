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

**The easy way — double-click `DJHelper.app`.**
The first launch opens a Terminal window, sets up a virtual environment, installs
dependencies, and opens the app in your browser. Every launch after that just
starts silently and opens **http://localhost:8765**.

**Or from the command line:**
```bash
git clone <your-repo-url> DJHelper
cd DJHelper
brew install ffmpeg           # required for audio extraction
./run.sh                      # sets up a venv, installs deps, opens the app
```

That's it — **no Spotify account or API keys required.** DJHelper reads public
playlists straight from Spotify's public embed data.

### Spotify credentials (optional)
You only need these for **private** playlists. Create a free app at
<https://developer.spotify.com/dashboard> and put the Client ID/Secret in `.env`.

> Spotify deprecated its audio-features/analysis API for new apps in late 2024,
> so DJHelper computes BPM/key/energy itself from the audio — which is more
> accurate for DJing anyway.

### Local AI (optional)
```bash
# install Ollama from https://ollama.com, then:
ollama pull gemma4:e2b      # small, fast edge model (default)
# fallbacks if that tag isn't available for you:
ollama pull gemma3n:e2b
ollama pull gemma2:2b
```
Set `OLLAMA_MODEL` in `.env` to match. If Ollama isn't running, DJHelper simply
uses the deterministic harmonic engine (which is excellent on its own) and the
AI toggle stays disabled.

---

## How it works

1. **Import** — paste a public Spotify playlist URL. DJHelper pulls the track list (no login).
2. **Download & analyze** — for each track it finds a matching file in your music folder, or downloads it with `yt-dlp` (toggleable), then analyzes it:
   - **BPM** via beat tracking (folded into a sane DJ range)
   - **Key** via Krumhansl-Schmuckler profiles → **Camelot** code
   - **Energy** from RMS loudness
   - **Mix-in cue** at the first downbeat, **Mix-out cue** N beats before the end
3. **Build the set** — greedy sequencing that balances:
   - harmonic compatibility (Camelot wheel),
   - BPM proximity (half/double-time aware),
   - an energy curve that rises to a peak then eases off.
   Tune the weights with the sliders. Turn on **AI set notes** to have Gemma
   read the finished set and describe its arc, peak, and any transitions to
   hand-mix. (The deterministic engine handles the *ordering* — a small edge
   model like `gemma4:e2b` can't out-sequence harmonic math, so Gemma's job is
   the read/narrative. A larger model may also re-rank; the app keeps whichever
   order is harmonically sound.)
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
DJHelper.app     double-click launcher (macOS)
run.sh           CLI launcher / first-run setup
backend/
  main.py        FastAPI app + serves the UI
  spotify.py     playlist import (credential-free embed scrape + API fallback)
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
