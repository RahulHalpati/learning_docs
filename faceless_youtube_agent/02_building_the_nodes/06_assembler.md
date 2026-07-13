# 02-6 · Assembler (ffmpeg)

> **Level:** Beginner · **Time:** 25 min

The assembler is the only node that produces video. It takes the slides, their
durations, and the narration track, and muxes them into one `.mp4` with ffmpeg.
This is `assembler` in [`nodes.py`](../99_project_faceless_studio/faceless_studio/nodes.py)
and `assemble_video` in [`media.py`](../99_project_faceless_studio/faceless_studio/media.py).

---

## The node

```python
def assembler(state, *, workdir: Path) -> dict:
    segments = state["segments"]
    durations = [float(s.get("duration") or media.estimate_duration(s["narration"]))
                 for s in segments]
    out = Path(workdir) / "video.mp4"
    media.assemble_video(state["image_paths"], durations, state["audio_path"], out)
    return {"video_path": str(out), "log": ["assembler"]}
```

It reads durations from the segments (with an estimate as a safety net) and hands
everything to `assemble_video`.

---

## Building a slideshow with ffmpeg's concat demuxer

ffmpeg turns a list of "show this image for N seconds" instructions into a video
via the **concat demuxer**. You write a text manifest:

```
file '/abs/path/slide_00.png'
duration 8.24
file '/abs/path/slide_01.png'
duration 6.10
file '/abs/path/slide_02.png'
duration 8.90
file '/abs/path/slide_02.png'
```

> The last image is listed **twice** (once without a duration). That's a
> well-known ffmpeg quirk: the final `duration` is otherwise ignored, so you repeat
> the last frame to make it stick.

Then the command:

```python
cmd = [
    ffmpeg, "-y",
    "-f", "concat", "-safe", "0", "-i", slides_manifest,
    "-i", audio_path,
    "-vf", f"fps={FPS},format=yuv420p",
    "-c:v", "libx264", "-c:a", "aac",
    "-shortest", out_path,
]
```

- **`-f concat`** reads the manifest of timed images.
- **`-vf fps=25,format=yuv420p`** sets a constant frame rate and a pixel format
  players actually support (skip `yuv420p` and some devices show a black screen).
- **`-c:v libx264 -c:a aac`** — the codecs YouTube and every browser expect.
- **`-shortest`** ends the video when the shorter of {slides, audio} ends, keeping
  them in sync.

### A graceful fallback

Some minimal ffmpeg builds lack `libx264`. The code catches the failure and retries
with the always-present `mpeg4` encoder:

```python
try:
    _run(cmd)
except RuntimeError:
    cmd[cmd.index("libx264")] = "mpeg4"
    _run(cmd)
```

Same philosophy as the LLM and TTS layers: **degrade, don't die.**

---

## Verified output

Running the offline pipeline produced this real file:

```bash
$ ffprobe out/big-o-notation-for-beginners/video.mp4
  Video: h264 (High), yuv420p, 1280x720, 25 fps
  Audio: aac, 44100 Hz, mono
  Duration: 00:00:23.24
```

Three timed slides + a narration track = a genuine, playable video, made with no
API key and no paid service. `test_full_pipeline_produces_mp4` in
[`tests/test_graph.py`](../99_project_faceless_studio/tests/test_graph.py) asserts
the file exists and is non-trivial.

---

## Recap

- The assembler is the **only** video-producing node — pure ffmpeg.
- The **concat demuxer** turns timed images into a slideshow; repeat the last frame
  to honor its duration.
- `yuv420p` + `libx264`/`aac` = maximum compatibility; `-shortest` keeps A/V synced.
- It **falls back to `mpeg4`** if `libx264` is missing.

## Self-check

1. Why is the last image listed twice in the concat manifest?
2. What does `-shortest` do, and why do we want it here?
3. Why force `format=yuv420p`?

<details>
<summary>Answers</summary>

1. ffmpeg ignores the final entry's `duration`; repeating the last frame makes the
   last slide display for its intended time.
2. It stops encoding when the shorter input (slides or audio) ends, so video and
   narration stay aligned instead of one trailing past the other.
3. Many players/devices only decode `yuv420p` chroma subsampling; without it the
   video can appear black or fail to play.

</details>

---

**Next → [02-7 · Metadata & SEO](07_metadata.md)**
