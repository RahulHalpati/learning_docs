# 01-3 · Inspecting with ffprobe

> **Level:** Beginner · **Prerequisites:** [01-2 · Containers, codecs & streams](02_containers_and_codecs.md)
> **Time:** 40 min · **Verified:** 2026-08-07 · ffprobe 4.4.2

## Why this matters

`ffprobe` is the debugger for media work. Every "why did that happen?" in this course is answered by probing the file. It's also how your code makes decisions — you can't decide whether to reframe a video without first knowing its aspect ratio.

Get fluent with it now and the rest of the course is diagnosis instead of guessing.

---

## The default output is for humans

```bash
ffprobe sample.mp4
```

**Output (real run, tail):**
```
  Stream #0:1(und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, mono, fltp, 73 kb/s (default)
    Metadata:
      handler_name    : SoundHandler
```

Readable, and completely unparseable from code. **Never scrape this.** The format has changed between versions and varies by codec.

---

## Two output modes that matter

### One value, no decoration

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 sample.mp4
```

**Output (real run):**
```
10.000000
```

Piece by piece:

| Flag | Effect |
|------|--------|
| `-v error` | suppress the banner and info logs — without it you get noise |
| `-show_entries format=duration` | just this one field |
| `-of csv=p=0` | CSV output, `p=0` = **no field name prefix** |

This is the shell one-liner form. Perfect in a bash script, still fragile in Python.

### JSON — the form to use from code

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt \
  -of json sample.mp4
```

**Output (real run):**
```json
{
    "programs": [],
    "streams": [
        {
            "codec_name": "h264",
            "width": 640,
            "height": 360,
            "pix_fmt": "yuv420p",
            "r_frame_rate": "25/1"
        }
    ]
}
```

`-select_streams v:0` means "the first video stream". Use `a:0` for the first audio stream, `v` for all video streams.

> **Tip:** `-of json` plus `json.loads()` is the only inspection method you should ever ship. It's stable across versions, handles missing fields gracefully, and gives you real types instead of strings you have to parse. The capstone's `probe()` is 20 lines built on exactly this.

---

## The fields worth knowing

### From `-show_format` (the container)

| Field | Meaning |
|-------|---------|
| `duration` | length in seconds ← the one you'll use most |
| `size` | bytes |
| `bit_rate` | overall bits/sec |
| `format_name` | container(s) — note MP4 reports a comma-joined family list |

**Output (real run, `-show_entries format=format_name`):**
```
mov,mp4,m4a,3gp,3g2,mj2
```

That's not six containers — it's one demuxer that handles all of them, reporting its full list. Don't string-compare it to `"mp4"`.

### From `-show_streams` (the tracks)

| Field | Meaning |
|-------|---------|
| `codec_type` | `video` / `audio` / `subtitle` |
| `codec_name` | `h264`, `aac`, … |
| `width`, `height` | video dimensions |
| `pix_fmt` | the trap from [01-2](02_containers_and_codecs.md) |
| `r_frame_rate` | frame rate as a **fraction** — `25/1`, or `30000/1001` for 29.97 |
| `sample_rate`, `channels` | audio properties |
| `nb_frames` | frame count, **if the container stored it** |

> ⚠️ **`r_frame_rate` is a string fraction, not a number.** `30000/1001` is NTSC's 29.97 fps. Parse it as `numerator / denominator` — `float("30000/1001")` raises, and truncating to `30` will drift your timestamps by 0.1%, which is a full second every 17 minutes.

---

## Counting frames: two answers, one correct

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of csv=p=0 sample.mp4
ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames -of csv=p=0 sample.mp4
```

**Output (real run):**
```
250      # nb_frames      — read from container metadata, instant
250      # nb_read_frames — actually decoded and counted, slow
```

They agree here. They **won't** agree for a stream where the metadata is missing or wrong (common in MKV, live recordings, and anything from a streaming download), where `nb_frames` returns `N/A`.

Use `nb_frames` for a quick estimate, `-count_frames` only when you need certainty and can afford a full decode.

---

## Keyframes — why your cut was off

This is the probe that explains a puzzle from the next section:

```bash
ffprobe -v error -select_streams v:0 -skip_frame nokey \
  -show_entries frame=pkt_pts_time -of csv=p=0 sample.mp4
```

**Output (real run):**
```
0.000000
```

**One keyframe, at the very start of a 250-frame file.** A keyframe is a frame encoded standalone; every other frame only stores the *difference* from its neighbours. A decoder can only start at a keyframe.

That single line is why `-c copy` cutting is imprecise ([02-2](../02_core_operations/02_trimming_and_cutting.md)): a stream copy can't produce a frame the decoder can't start on, so it snaps to the nearest keyframe. With one keyframe in the whole file, "nearest" isn't near.

> **Tip:** When you control the encode, `-g 50` forces a keyframe every 50 frames (2 seconds at 25 fps). More keyframes = larger files but faster seeking and more precise copy-cuts. Streaming formats like HLS require them at segment boundaries for this exact reason.

---

## Probing a broken file

```bash
head -c 2000 sample.mp4 > broken.mp4        # truncate it
ffprobe -v error -show_entries format=duration -of csv=p=0 broken.mp4; echo "exit=$?"
```

**Output (real run):**
```
[mov,mp4,m4a,3gp,3g2,mj2 @ 0x5b9d966a2e40] moov atom not found
broken.mp4: Invalid data found when processing input
exit=1
```

Two things to notice, both of which shape the toolkit in [06-1](../06_python_automation/01_subprocess_basics.md):

1. **The error went to stderr, and stdout was empty.** Code that only reads stdout sees a blank string and may treat it as a duration of zero.
2. **The exit code is 1.** That's the reliable signal — always check it.

> ⚠️ **Validate uploads by probing them.** A file with a `.mp4` extension is not a video; it's a filename. Probing is a cheap, effective validity check before you commit expensive processing to a job queue — and it's a security boundary too, since "it has a video extension" is trivially forged.

The `moov atom` here is MP4's index. It's often written *last*, which is why a partially-uploaded MP4 is completely unreadable rather than partially readable. (`-movflags +faststart` moves it to the front, which is what makes web video start playing before it's fully downloaded.)

---

## From the capstone

```python
def probe(path: str | Path) -> dict:
    out = run(["-v", "error", "-print_format", "json",
               "-show_format", "-show_streams", str(path)], binary="ffprobe")
    data = json.loads(out)
    fmt = data.get("format", {})
    return {
        "duration": float(fmt.get("duration", 0.0)),
        "size": int(fmt.get("size", 0)),
        "format": fmt.get("format_name", ""),
        "streams": [...],
    }
```

**Output (real run, `python -m mediakit probe talk.mp4`):**
```json
{
  "duration": 12.0,
  "size": 159468,
  "format": "mov,mp4,m4a,3gp,3g2,mj2",
  "streams": [
    { "type": "video", "codec": "h264", "width": 640, "height": 360,
      "sample_rate": null, "channels": null },
    { "type": "audio", "codec": "aac", "width": null, "height": null,
      "sample_rate": "44100", "channels": 1 }
  ]
}
```

Note `.get()` with defaults everywhere — probe output is genuinely inconsistent between formats, and a `KeyError` on an unusual upload is a production incident you can avoid for free.

---

## Recap & next

- ✅ **Never parse ffprobe's default output.** Use `-of json` from code, `-of csv=p=0` in shell one-liners.
- ✅ `-v error` suppresses the banner; without it your JSON has garbage in front of it.
- ✅ `r_frame_rate` is a **fraction string** — `30000/1001`, not `29.97`. Parse, don't truncate.
- ✅ `nb_frames` is metadata (instant, sometimes `N/A`); `-count_frames` decodes (slow, exact).
- ✅ Our sample has **one keyframe** — that's why copy-cutting is imprecise.
- ✅ On a broken file, **stdout is empty and the exit code is 1**. Check the exit code, not the output.
- ✅ **Probe uploads to validate them** — an extension is not a format.
- ✅ Self-check: `nb_frames` returns `N/A` on a user's upload. What do you do, and what does it cost?

→ Next: **[02 · Core operations](../02_core_operations/README.md)**

## Exercises

1. Write a one-liner that prints just a video's resolution as `WIDTHxHEIGHT`.

<details>
<summary>Solution</summary>

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
        -of csv=s=x:p=0 sample.mp4
# 640x360
```
`-of csv=s=x` sets the separator to `x`. A small demonstration of a real principle: get the tool to format the output rather than post-processing it.
</details>

2. Compute a video's frame rate as a float in Python, correctly handling `30000/1001`.

<details>
<summary>Solution</summary>

```python
from fractions import Fraction
rate = float(Fraction(stream["r_frame_rate"]))   # 29.97002997002997
```
`Fraction` parses `"a/b"` natively — no split, no ZeroDivisionError guard needed for the well-formed case. Worth using over manual splitting because it also handles the plain `"25"` form that some streams report.
</details>
