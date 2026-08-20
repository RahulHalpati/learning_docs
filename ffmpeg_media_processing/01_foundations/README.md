# 01 · Foundations

> **Level:** Beginner · **Prerequisites:** [00 · Introduction](../00_introduction.md)
> **Time:** ~2 hours

Before you transform media, you need to be able to *read* it. This section covers the vocabulary (container, codec, stream, bitrate, frame rate) and the one tool you'll use more than any other: `ffprobe`.

The payoff is diagnostic. When a video won't play on a phone, or a clip is silent, or a file is inexplicably 400 MB, the answer is always visible in the probe output — if you know what you're looking at.

| # | Module | You'll be able to… |
|---|--------|--------------------|
| 1 | [Anatomy of a command](01_anatomy_of_a_command.md) | Read and write ffmpeg command lines; know where flags go and why order matters |
| 2 | [Containers, codecs & streams](02_containers_and_codecs.md) | Explain MP4 vs H.264; pick a container; avoid the pixel-format trap |
| 3 | [Inspecting with ffprobe](03_inspecting_with_ffprobe.md) | Extract any property of any media file, as JSON, from code |

→ Start: **[01-1 · Anatomy of a command](01_anatomy_of_a_command.md)**
