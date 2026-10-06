#!/usr/bin/env python3
"""
Trail Notebook
==============
Offline field journal for a walk:

  1. BirdNET (open-source audio model, via birdnetlib) identifies bird calls
     in a recording made on the trail.
  2. A small local LLM served by Ollama (open weights) turns the detections
     into a short field-journal entry. No cloud, no API key, no signal needed.
  3. The entry is saved as a Markdown file you can read or print later.

Usage examples
--------------
  python trail_notebook.py walk.wav
  python trail_notebook.py walk.wav --lat 12.97 --lon 77.59 --date 2026-10-06
  python trail_notebook.py walk.wav --model qwen2.5:3b --note "Misty morning, lake loop"
  python trail_notebook.py --demo            # no audio or BirdNET needed
  python trail_notebook.py walk.wav --no-llm # template journal, Ollama not needed
"""
import argparse
import datetime as dt
import re
import sys
from collections import defaultdict
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "gemma3:4b"
DEFAULT_RECORDINGS_DIR = Path(__file__).resolve().parent / "Recordings"
SUPPORTED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}

DEMO_DETECTIONS = [
    {"common_name": "Common Tailorbird", "scientific_name": "Orthotomus sutorius",
     "start_time": 12.0, "end_time": 15.0, "confidence": 0.81},
    {"common_name": "Common Tailorbird", "scientific_name": "Orthotomus sutorius",
     "start_time": 95.0, "end_time": 98.0, "confidence": 0.74},
    {"common_name": "Asian Koel", "scientific_name": "Eudynamys scolopaceus",
     "start_time": 140.0, "end_time": 143.0, "confidence": 0.92},
    {"common_name": "Oriental Magpie-Robin", "scientific_name": "Copsychus saularis",
     "start_time": 210.0, "end_time": 213.0, "confidence": 0.66},
]


def create_analyzer():
    """Load BirdNET once so batch runs can reuse its model."""
    try:
        from birdnetlib.analyzer import Analyzer
    except ImportError as exc:
        sys.exit(f"BirdNET dependencies are unavailable ({exc}). Run: pip install -r requirements.txt")
    return Analyzer()


def detect_birds(audio_path, lat, lon, date, min_conf, analyzer):
    """Run BirdNET on an audio file and return a list of detection dicts."""
    try:
        from birdnetlib import Recording
    except ImportError as exc:
        sys.exit(f"BirdNET dependencies are unavailable ({exc}). Run: pip install -r requirements.txt")

    kwargs = {"min_conf": min_conf}
    if lat is not None and lon is not None:
        kwargs["lat"], kwargs["lon"] = lat, lon
    if date is not None:
        kwargs["date"] = date

    recording = Recording(analyzer, str(audio_path), **kwargs)
    recording.analyze()
    return recording.detections


def discover_recordings(directory):
    """Return supported audio files in a directory, sorted by filename."""
    directory = Path(directory).expanduser()
    if not directory.is_dir():
        return []
    return sorted(
        (path for path in directory.iterdir()
         if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES),
        key=lambda path: path.name.casefold(),
    )


def choose_recordings(audio_inputs, recordings_dir, browse, all_recordings):
    """Resolve explicit paths, a file-picker choice, or the recordings folder."""
    if browse:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except ImportError as exc:
            raise ValueError("File browsing needs tkinter; pass an audio path instead.") from exc

        try:
            root = tk.Tk()
            root.withdraw()
            selected = filedialog.askopenfilenames(
                title="Choose trail recordings",
                initialdir=str(Path(recordings_dir).expanduser()),
                filetypes=[("Audio recordings", "*.wav *.mp3 *.m4a *.flac *.ogg"),
                           ("All files", "*.*")],
            )
            root.destroy()
        except tk.TclError as exc:
            raise ValueError(f"Could not open the file picker: {exc}") from exc
        audio_inputs = selected

    if audio_inputs:
        recordings = []
        for audio_input in audio_inputs:
            path = Path(audio_input).expanduser()
            if path.is_dir():
                recordings.extend(discover_recordings(path))
            elif not path.is_file():
                raise ValueError(f"Recording not found: {path}")
            elif path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
                raise ValueError(f"Unsupported audio format: {path.suffix}")
            else:
                recordings.append(path)
    else:
        recordings = discover_recordings(recordings_dir)

    recordings = list(dict.fromkeys(path.resolve() for path in recordings))
    if not recordings:
        raise ValueError(
            f"No audio recordings found. Add files to '{recordings_dir}', "
            "pass a file or folder path, or use --browse."
        )
    if audio_inputs or browse or all_recordings:
        return recordings

    print(f"Recordings in '{recordings_dir}':")
    for index, path in enumerate(recordings, start=1):
        print(f"  {index}. {path.name}")
    choice = input("Choose numbers separated by commas, or 'all': ").strip().lower()
    if choice == "all":
        return recordings
    try:
        indexes = [int(value.strip()) for value in choice.split(",")]
        if not indexes or any(index < 1 or index > len(recordings) for index in indexes):
            raise ValueError
    except ValueError as exc:
        raise ValueError("Choose valid recording numbers, or type 'all'.") from exc
    return [recordings[index - 1] for index in dict.fromkeys(indexes)]


def unique_output_path(out_dir, date_str, audio_path):
    """Build a readable output name from the recording and avoid overwrites."""
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", audio_path.stem).strip("._")
    safe_stem = safe_stem or "recording"
    timestamp = dt.datetime.now().strftime("%H%M%S")
    output_path = out_dir / f"{date_str}_{safe_stem}_{timestamp}.md"
    suffix = 2
    while output_path.exists():
        output_path = out_dir / f"{date_str}_{safe_stem}_{timestamp}_{suffix}.md"
        suffix += 1
    return output_path


def summarize(detections):
    """Collapse raw detections into one row per species."""
    groups = defaultdict(list)
    for d in detections:
        groups[(d["common_name"], d["scientific_name"])].append(d)

    rows = []
    for (common, sci), items in groups.items():
        rows.append({
            "common_name": common,
            "scientific_name": sci,
            "count": len(items),
            "best_confidence": max(i["confidence"] for i in items),
            "first_heard": min(i["start_time"] for i in items),
        })
    rows.sort(key=lambda r: (-r["count"], -r["best_confidence"]))
    return rows


def mmss(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def build_prompt(rows, note, date_str):
    species_lines = "\n".join(
        f"- {r['common_name']} ({r['scientific_name']}): heard {r['count']}x, "
        f"best confidence {r['best_confidence']:.0%}, first at {mmss(r['first_heard'])}"
        for r in rows
    )
    return (
        f"Date of walk: {date_str}\n"
        f"Walker's note: {note or 'none'}\n\n"
        f"Birds detected by an audio classifier:\n{species_lines}\n\n"
        "Write a short field-journal entry (120-180 words) in a warm, observant "
        "first-person voice. Mention only the species listed above; do not add "
        "any species, places or facts not given. Where confidence is below 60%, "
        "say the identification is tentative. End with one sentence encouraging "
        "the reader to go back outside and listen again."
    )


def call_ollama(model, prompt, url=OLLAMA_URL, timeout=180):
    """Return the model's text, or None if Ollama is unreachable."""
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.3},
        "messages": [
            {"role": "system",
             "content": "You are a careful naturalist writing a trail journal. "
                        "You never invent observations."},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except (requests.RequestException, KeyError, ValueError) as exc:
        print(f"[warn] Ollama call failed ({exc}); using template journal.",
              file=sys.stderr)
        return None


def template_journal(rows, note):
    names = ", ".join(r["common_name"] for r in rows)
    text = f"On this walk I heard: {names}."
    if note:
        text += f" Note: {note.rstrip('.')}."
    tentative = [r["common_name"] for r in rows if r["best_confidence"] < 0.6]
    if tentative:
        text += f" Tentative identifications: {', '.join(tentative)}."
    return text + " Time to go back outside and listen again."


def render_markdown(rows, narrative, date_str, source, model_used):
    lines = [
        f"# Trail Notebook, {date_str}",
        "",
        f"_Recording: {source}_",
        "",
        "## Field note",
        "",
        narrative,
        "",
        "## Species heard",
        "",
        "| Species | Scientific name | Times | Best confidence | First heard |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['common_name']} | {r['scientific_name']} | {r['count']} | "
            f"{r['best_confidence']:.0%} | {mmss(r['first_heard'])} |"
        )
    lines += [
        "",
        f"_Identified offline with BirdNET. Journal text by: {model_used}._",
        "",
    ]
    return "\n".join(lines)


def parse_args():
    p = argparse.ArgumentParser(description="Offline bird-call field journal.")
    p.add_argument("audio", nargs="*", help="Audio file(s) or folder(s) to analyze")
    p.add_argument("--recordings-dir", default=str(DEFAULT_RECORDINGS_DIR),
                   help="Folder to browse when no audio path is given (default: Recordings)")
    p.add_argument("--browse", action="store_true",
                   help="Choose one or more recordings in a file picker")
    p.add_argument("--all", action="store_true",
                   help="Analyze every supported recording in --recordings-dir")
    p.add_argument("--lat", type=float, help="Latitude (improves species filtering)")
    p.add_argument("--lon", type=float, help="Longitude")
    p.add_argument("--date", help="Walk date, YYYY-MM-DD (default: today)")
    p.add_argument("--min-conf", type=float, default=0.4,
                   help="Minimum BirdNET confidence, 0-1 (default 0.4)")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"Ollama model name (default {DEFAULT_MODEL})")
    p.add_argument("--note", help="Your own note about the walk")
    p.add_argument("--out-dir", default="journal", help="Where to save entries")
    p.add_argument("--no-llm", action="store_true",
                   help="Skip Ollama and write a simple template journal")
    p.add_argument("--demo", action="store_true",
                   help="Use built-in sample detections (no audio/BirdNET needed)")
    return p.parse_args()


def main():
    args = parse_args()

    if args.demo and (args.audio or args.browse or args.all):
        sys.exit("--demo cannot be combined with recording inputs.")
    if args.browse and (args.audio or args.all):
        sys.exit("Use only one of --browse, --all, or explicit recording paths.")
    if args.all and args.audio:
        sys.exit("Pass recording paths or use --all, not both.")

    walk_date = (dt.datetime.strptime(args.date, "%Y-%m-%d")
                 if args.date else dt.datetime.now())
    date_str = walk_date.strftime("%Y-%m-%d")

    if args.demo:
        recordings = [None]
    else:
        try:
            recordings = choose_recordings(
                args.audio, args.recordings_dir, args.browse, args.all
            )
        except ValueError as exc:
            sys.exit(str(exc))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = 0
    analyzer = None
    for audio_path in recordings:
        if args.demo:
            detections, source = DEMO_DETECTIONS, "demo data"
        else:
            print(f"\nAnalyzing '{audio_path.name}' with BirdNET...")
            if analyzer is None:
                analyzer = create_analyzer()
            detections = detect_birds(audio_path, args.lat, args.lon,
                                      walk_date, args.min_conf, analyzer)
            source = audio_path.name

        if not detections:
            print(f"[warn] No birds detected in '{source}'. Try --min-conf 0.25.",
                  file=sys.stderr)
            continue

        rows = summarize(detections)
        print(f"Detected {len(rows)} species in '{source}'.")

        narrative, model_used = None, "template"
        if not args.no_llm:
            print(f"Writing journal with local model '{args.model}'...")
            narrative = call_ollama(
                args.model, build_prompt(rows, args.note, date_str)
            )
            if narrative:
                model_used = f"{args.model} via Ollama"
        if not narrative:
            narrative = template_journal(rows, args.note)

        md = render_markdown(rows, narrative, date_str, source, model_used)
        out_path = unique_output_path(
            out_dir, date_str, Path("demo") if args.demo else audio_path
        )
        out_path.write_text(md, encoding="utf-8")
        print("\n" + md)
        print(f"Saved to {out_path}")
        saved += 1

    if not saved:
        sys.exit("No journals were saved. Try --min-conf 0.25 or a clearer recording.")
    print(f"\nFinished: saved {saved} journal(s) to {out_dir}.")


if __name__ == "__main__":
    main()
