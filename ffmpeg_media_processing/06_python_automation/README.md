# 06 · Python automation

> **Level:** Intermediate → Advanced · **Prerequisites:** [05 · Encoding & quality](../05_encoding/README.md)
> **Time:** ~3 hours

Knowing the commands is half of it. The other half is driving them from an application — reliably, with real error messages, progress reporting, and a way to know whether a job actually worked.

This section builds the toolkit the capstone ships, and ends with the piece that makes it an *AI* video pipeline: turning speech into timestamped text, for free.

| # | Module | You'll be able to… |
|---|--------|--------------------|
| 1 | [Running ffmpeg from Python](01_subprocess_basics.md) | Call ffmpeg safely; surface real errors; avoid the shell-injection trap |
| 2 | [Progress & long jobs](02_progress_and_jobs.md) | Report progress, time out, cancel, and run video work off the request path |
| 3 | [Analysis: silence & scenes](03_analysis.md) | Find cut points with no model and no cost |
| 4 | [Transcription with faster-whisper](04_transcription.md) | Generate timestamped captions locally, free — and know when to pay instead |

→ Start: **[06-1 · Running ffmpeg from Python](01_subprocess_basics.md)**
