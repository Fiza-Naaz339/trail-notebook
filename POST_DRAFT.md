---
title: "Trail Notebook: Offline Birding with BirdNET and Gemma"
published: false
description: "A local-first field journal that turns trail recordings into bird detections and Markdown notes using BirdNET and Gemma, without uploading audio."
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05).*

## What I Built

Trail Notebook is a small offline field journal for people who want to remember the sounds of a walk without spending the walk looking at a screen.

The workflow is simple: record birdsong while outside, put the phone away, and analyze the recording later. BirdNET identifies candidate bird calls. A local language model then turns those detections into a short journal entry, and the app saves the result as Markdown alongside a table of species, confidence scores, and the first time each species was heard.

The important design choice is that the recording stays on the device. BirdNET runs locally, and the journal writer uses Ollama on the local machine. There is no audio upload or hosted API in the workflow.

## Demo

**Add before publishing:** embed a short video showing a real recording being selected, analyzed, and saved as a journal. The project also has a sample-data mode for demonstrating the output format, but sample detections are not real field observations.

## Code

**Add your public repository URL before publishing:**

`{% embed https://github.com/YOUR_USERNAME/trail-notebook %}`

## How It Works

- **BirdNET**, through `birdnetlib`, analyzes an audio recording and returns candidate species with confidence scores and timestamps.
- **Ollama** runs an open-weight model locally. The default is `gemma3:4b`; another installed Ollama model can be selected with `--model`.
- The Python CLI groups detections by species and asks the model to write from that list rather than inventing additional observations. If Ollama is unavailable, the app falls back to a short template entry.
- Each journal is saved as a Markdown file named from the recording, which makes batch results easier to identify and avoids overwriting earlier entries.

To try the sample journal without audio or BirdNET:

```powershell
python trail_notebook.py --demo --no-llm
```

To choose a recording from the local file picker:

```powershell
python trail_notebook.py --browse
```

The app can also prompt from the project's `Recordings/` folder or process multiple recordings. Setup details are in the repository README.

## Why Open Innovation Matters

Birding recordings can reveal where someone walks and what they are listening for. Keeping both the audio and the model inference local means I do not have to send that data to a service I do not control. Once the models and dependencies are installed, the workflow can run without a network connection and without per-recording API charges.

Using an open-weight model locally also makes the writing step replaceable. I can compare models or change the prompt without changing the detection pipeline. The model is there to help organize the observations, not to decide what was actually present: BirdNET can misidentify calls, especially in noisy recordings, so confidence scores and the original recording still matter. The generated note should be reviewed rather than treated as ground truth.

## Taking It Outside

**Complete this section after a real field test:** add where and when you recorded, how long the recording was, what BirdNET detected, which identifications you checked by ear or against another source, and what worked or failed. Do not use the built-in demo species as walk results.

## Best Use of Gemma

Trail Notebook uses `gemma3:4b` as its default local journal-writing model through Ollama. The model can be changed with a command-line option, but Gemma makes the default workflow available locally without sending the recording or detection list to a hosted model API.

## My Agent Session

Optional: add an agent-session link or embed after saving the session.