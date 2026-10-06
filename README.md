# Trail Notebook

Offline bird-call field journal. Record a walk, put the phone away, read the journal later.

- **BirdNET** (open-source audio model, via `birdnetlib`) identifies the birds.
- **A local LLM via Ollama** (open weights, e.g. Gemma) writes the field note.
- No cloud, no API keys, no signal needed after setup.

## Setup

### 1. Install prerequisites

- Install Python 3.10 or 3.11. On Windows, select the option to add Python to PATH.
- Install FFmpeg if your recordings are MP3 or M4A. WAV files do not need it.
   - Windows: `winget install --id Gyan.FFmpeg --exact`, then close and reopen PowerShell.
   - macOS: `brew install ffmpeg`.
   - Ubuntu/Debian: `sudo apt install ffmpeg`.
- Ollama is optional. Install it from [ollama.com](https://ollama.com) if you want
   AI-written journal text. To use the default model, run `ollama pull gemma3:4b`.
   You can skip Ollama and use `--no-llm` for a simple template journal.

Check that FFmpeg is available in a new terminal with `ffmpeg -version`.
Installing a Python package named `ffmpeg` with pip does not install the FFmpeg program.

### 2. Open the project folder in a terminal

Change to the folder containing `trail_notebook.py`. For example, in PowerShell:

```powershell
cd D:\trail-notebook
```

### 3. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

If PowerShell blocks activation, allow it for this terminal only, then activate:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Install Python dependencies

With the virtual environment active, run:

```powershell
python -m pip install -r requirements.txt
```

### 5. Run a demo first

This checks the journal workflow without needing a recording or BirdNET model:

```powershell
python trail_notebook.py --demo --no-llm
```

It prints a sample journal and saves it in `journal/`.

## Run With Your Recordings

Put audio files in the project's `Recordings/` folder, then run:

```powershell
python trail_notebook.py
```

Choose one or more files from the numbered list. Other ways to select recordings:

```powershell
python trail_notebook.py --browse                    # open a file picker
python trail_notebook.py --all                       # process Recordings/
python trail_notebook.py Recordings                   # process a folder
python trail_notebook.py "Recordings\walk one.mp3"    # process one file
python trail_notebook.py walk1.wav walk2.mp3          # process multiple files
```

By default, the app uses Ollama to write the journal. Make sure Ollama is running
and the model has been downloaded. Add `--no-llm` to skip it:

```powershell
python trail_notebook.py --all --no-llm
```

Optional location and journal settings:

```powershell
python trail_notebook.py walk.wav --lat 12.97 --lon 77.59 --date 2026-10-06 --note "Lake loop"
python trail_notebook.py walk.wav --model qwen2.5:3b
python trail_notebook.py --all --recordings-dir "D:\My Walks" --out-dir journals
```

Supported formats: WAV, MP3, M4A, FLAC, and OGG. Use `--recordings-dir` to choose
another folder. Recordings are processed locally and never uploaded. Journals are
saved as Markdown in `journal/`, with names based on the recording so existing
entries are not overwritten.

## Notes

- Add `--lat/--lon/--date` so BirdNET only considers birds plausible for that place and season.
- Lower `--min-conf` (for example 0.25) for noisy recordings.
- The prompt restricts the LLM to the detected species. Low-confidence detections are labelled tentative.
