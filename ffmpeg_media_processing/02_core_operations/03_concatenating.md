# 02-3 · Concatenating

> **Level:** Intermediate · **Prerequisites:** [02-2 · Trimming & cutting](02_trimming_and_cutting.md)
> **Time:** 40 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2

## Why this matters

Joining clips is how you assemble anything: a montage, a slideshow, a video with a section removed, a generated video built from rendered segments. ffmpeg offers two completely different mechanisms for it, and choosing wrong gives you either a wasted transcode or — much worse — **a corrupt file that reports success**.

---

## Method 1: the concat demuxer (fast)

For clips that already share a codec, resolution, and frame rate:

```bash
printf "file 'part1.mp4'\nfile 'part2.mp4'\n" > list.txt
ffmpeg -y -f concat -safe 0 -i list.txt -c copy joined.mp4
```

**Output (real run, joining two 3.0s clips):**
```
  joined duration = 6.024000
```

Stream copy, so it's near-instant regardless of length. This is the right method the overwhelming majority of the time, because most concat jobs are joining pieces **you produced yourself** — and you control their format.

Notes on the list file:

- Paths are wrapped in **single quotes**; a literal `'` in a filename must be escaped as `'\''`.
- `-safe 0` allows absolute paths. Without it ffmpeg rejects them as a security measure (the list file is untrusted input in some deployments).
- Relative paths resolve against the **list file's** directory, not your working directory. Absolute paths avoid the confusion entirely.

That last point is why the capstone resolves everything before writing the list:

```python
def concat(parts, dst, *, workdir=None):
    parts = [Path(p).resolve() for p in parts]
    if not parts:
        raise ValueError("concat() needs at least one part")
    listfile = Path(workdir or Path(dst).parent) / "_concat.txt"
    listfile.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(dst)])
    listfile.unlink(missing_ok=True)
    return Path(dst)
```

---

## The silent corruption trap

Here is what happens when the inputs *don't* match. Two 3-second clips, one H.264 and one MPEG-4:

```bash
printf "file 'm1.mp4'\nfile 'c_mpeg4.mp4'\n" > cl.txt
ffmpeg -y -f concat -safe 0 -i cl.txt -c copy mixed.mp4
```

**Output (real run):**
```
  exit code        : 0
  duration         : 6.024000        ← correct!
  decodable frames : 75              ← should be 150
  decode errors    : 140
```

Read that again. **ffmpeg exited successfully. The duration is right. Half the video is destroyed.**

Nothing in the exit code or the probe tells you. The only way to find out is to decode the file and count what survives — which is exactly what that measurement did:

```bash
ffmpeg -v error -i mixed.mp4 -f null -          # decode everything, print only errors
```

> ⚠️ **The concat demuxer does not validate that your inputs are compatible.** It concatenates packets and trusts you. A zero exit code from a concat job is not evidence the output is good. If your pipeline joins files it didn't produce, verify the output by decoding it — or use the concat filter and don't take the risk.

> **Honest note:** ffmpeg 4.4 is more tolerant than the folklore suggests. Joining two H.264 clips of *different resolutions* (640×360 + 320×240) decoded cleanly here — all 150 frames, zero errors. Codec mismatches are the reliably fatal case; resolution mismatches are player-dependent, so they'll work on your machine and fail on someone's TV. Neither is worth gambling on.

---

## Method 2: the concat filter (safe)

When inputs differ, normalise them in the same command and let the filter join decoded frames:

```bash
ffmpeg -y -i m1.mp4 -i m2.mp4 -filter_complex \
  "[0:v]scale=640:360,setsar=1[v0];\
   [1:v]scale=640:360,setsar=1[v1];\
   [v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -pix_fmt yuv420p -c:a aac good.mp4
```

**Output (real run):**
```
  duration        : 6.038000
  resolution      : 640x360
  decodable frames: 150
```

All 150 frames intact. Breaking the filtergraph down ([03-1](../03_filters/01_filtergraphs.md) covers the syntax properly):

| Part | Meaning |
|------|---------|
| `[0:v]scale=640:360,setsar=1[v0]` | take input 0's video, scale it, label the result `v0` |
| `[v0][0:a][v1][1:a]` | the inputs to concat, **interleaved v,a,v,a** |
| `concat=n=2:v=1:a=1[v][a]` | join 2 segments, each with 1 video + 1 audio, outputting `v` and `a` |
| `-map "[v]" -map "[a]"` | select those labelled outputs for the file |

> ⚠️ **The stream order is interleaved per segment, not grouped by type.** For two segments it's `[v0][a0][v1][a1]` — *not* `[v0][v1][a0][a1]`. Getting this backwards produces a confusing error or, worse, a file with the audio and video from different segments. It's the single most common concat-filter mistake.

`setsar=1` normalises the *sample aspect ratio*. Clips from different sources sometimes carry non-square pixel flags, and mixing them stretches half your output. It costs nothing and prevents a bug that's baffling to diagnose.

---

## Choosing

| | Concat demuxer | Concat filter |
|---|---|---|
| **Speed** | instant (stream copy) | full re-encode |
| **Quality** | lossless | one generation of loss |
| **Requires matching inputs** | yes | no |
| **Silent failure risk** | **yes** | no |
| **Use for** | pieces you produced yourself | mixed sources, user uploads |

**The pragmatic strategy for a pipeline handling arbitrary input:** normalise every clip to a house format as it arrives (one encode you were going to pay for anyway), then use the fast demuxer for all joins afterwards. You get safety at the boundary and speed everywhere inside.

---

## Adding music or a voiceover

Not concatenation — that's *mixing*, along a different axis:

```bash
# replace the audio entirely
ffmpeg -y -i video.mp4 -i music.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4

# mix narration over background music
ffmpeg -y -i narration.wav -i music.mp3 \
  -filter_complex "[1:a]volume=0.2[bg];[0:a][bg]amix=inputs=2:duration=first[a]" \
  -map "[a]" out.m4a
```

`volume=0.2` ducks the music to 20% so speech stays intelligible, and `duration=first` ends the mix with the narration rather than the music. `-c:v copy` in the first command is the [02-1](01_converting.md) rule again: the video isn't changing, so don't re-encode it.

---

## Recap & next

- ✅ **Concat demuxer** = stream copy, instant, requires matching inputs.
- ✅ **It does not validate compatibility.** Mismatched codecs gave **exit 0, correct duration, and half the frames destroyed**.
- ✅ A zero exit code is not proof of a good output — verify by decoding (`ffmpeg -v error -i out.mp4 -f null -`).
- ✅ **Concat filter** re-encodes but handles any inputs; normalise with `scale` + `setsar=1` first.
- ✅ Filter inputs are **interleaved per segment** (`[v0][a0][v1][a1]`), not grouped by type.
- ✅ Best strategy: **normalise on ingest, demux-concat forever after.**
- ✅ Self-check: your concat job exits 0 and the duration is right. What have you actually verified?

→ Next: **[02-4 · Extracting audio](04_extracting_audio.md)**

## Exercises

1. Join two copies of a clip with the demuxer, then verify the output is genuinely intact.

<details>
<summary>Solution</summary>

```bash
printf "file 'clip.mp4'\nfile 'clip.mp4'\n" > l.txt
ffmpeg -y -f concat -safe 0 -i l.txt -c copy out.mp4
ffmpeg -v error -i out.mp4 -f null -            # silence = clean
ffprobe -v error -select_streams v:0 -count_frames \
        -show_entries stream=nb_read_frames -of csv=p=0 out.mp4
```
The decode pass is the check that matters. Joining a file with itself is guaranteed-matching input, so this should be clean — which makes it a good baseline for recognising what a *broken* one looks like.
</details>

2. Why does the "normalise on ingest, then demux-concat" strategy avoid an extra generation of loss compared to using the concat filter for every join?

<details>
<summary>Solution</summary>

Because arbitrary uploads need one normalising encode regardless — you can't ship a user's random codec. Doing that once on arrival means every subsequent join is a lossless stream copy. Using the concat filter instead adds a *second* encode at every join, and a clip joined into three different compilations pays that cost three times.
</details>
