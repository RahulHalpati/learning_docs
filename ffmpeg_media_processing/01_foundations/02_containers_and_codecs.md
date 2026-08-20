# 01-2 · Containers, codecs & streams

> **Level:** Beginner · **Prerequisites:** [01-1 · Anatomy of a command](01_anatomy_of_a_command.md)
> **Time:** 40 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2

## Why this matters

"MP4" is not a video format. It's a box. What's *inside* the box is the video format. Conflating the two is the single most common source of confusion in media work, and it produces questions like "why won't my MP4 play on this device?" that are unanswerable until you separate the concepts.

---

## The two layers

> **Analogy:** A container is a **shipping box**; a codec is the **language the contents are written in**. Renaming the box (MP4 → MKV) doesn't translate the contents. Translating the contents (H.264 → H.265) is slow, lossy work that has nothing to do with the box.

| Layer | What it does | Examples |
|-------|--------------|----------|
| **Container** | Holds streams together, stores timing and metadata | MP4, MKV, MOV, WebM, AVI |
| **Codec** | Compresses one stream's actual data | H.264, H.265, VP9, AV1 / AAC, MP3, Opus |
| **Stream** | One track inside the container | video, audio, subtitle, data |

A single MP4 typically holds one H.264 video stream and one AAC audio stream. It could hold five audio streams and three subtitle tracks. The container doesn't care.

### Proving it: remux vs transcode

Changing the **container** while keeping the streams is called *remuxing*. It's a repackaging operation:

```bash
ffmpeg -y -i sample.mp4 -c copy out.mkv       # remux: change box, keep contents
ffmpeg -y -i sample.mp4 -c:v libx264 -crf 23 -c:a aac out2.mp4   # transcode
```

**Output (real run):**
```
  remux (-c copy)   : 0.05s
  transcode         : 0.41s
```

**8× faster**, on a 10-second file — and the gap grows linearly with duration. On a 2-hour recording that's seconds versus tens of minutes.

**Output (real run, file sizes):**
```
sample.mp4  159525 bytes
out.mkv     155322 bytes    ← same video data, different container overhead
```

The 4 KB difference is container structure, not video. **The pixels were never touched.**

> **Tip:** Whenever a task feels slow, ask: *does this actually require re-encoding?* Changing containers, dropping a stream, cutting on a keyframe, and editing metadata are all copy operations. Only pixel or sample changes require a transcode.

---

## Choosing a container

| Container | Use when | Watch out for |
|-----------|----------|---------------|
| **MP4** | default for delivery — web, mobile, social | can't hold every codec; poor for streaming *while writing* |
| **MKV** | archival, work-in-progress, anything unusual | not supported by browsers or most social platforms |
| **MOV** | Apple ecosystem, ProRes intermediates | large files |
| **WebM** | browser-native open formats (VP9/AV1 + Opus) | slower encodes, no H.264 |

For anything you'll upload, **MP4 with H.264 + AAC** is the answer. It is the most universally playable combination that exists.

---

## Choosing a video codec

| Codec | Encoder | Size at equal quality | Support |
|-------|---------|----------------------|---------|
| **H.264** | `libx264` | baseline | universal — every browser, phone, TV |
| **H.265 / HEVC** | `libx265` | ~50% smaller | good but patent-encumbered; no Firefox/Chrome by default |
| **VP9** | `libvpx-vp9` | ~50% smaller | browsers yes, hardware players patchy |
| **AV1** | `libaom-av1` | ~30% smaller than H.265 | newest, best compression, slowest to encode |
| **MPEG-4 Part 2** | `mpeg4` | ~2× larger | the fallback when libx264 is absent |

**Use libx264 unless you have a specific reason not to.** "Smaller files" is rarely worth "doesn't play on the user's device". Storage is cheap; a video that won't play is a bug.

Audio is simpler: **AAC** for MP4 (`-c:a aac`), **Opus** for WebM, **MP3** (`libmp3lame`) only for legacy compatibility, and **PCM** (`pcm_s16le`) for uncompressed intermediates — which is what speech-to-text wants ([02-4](../02_core_operations/04_extracting_audio.md)).

---

## The pixel-format trap

This one costs people hours, and it's invisible until the file reaches a real device.

```bash
ffmpeg -y -f lavfi -i "testsrc=size=320x240:rate=25:duration=1" -c:v libx264 nopix.mp4
ffprobe -v error -select_streams v -show_entries stream=pix_fmt -of csv=p=0 nopix.mp4
```

**Output (real run):**
```
  default pix_fmt: yuv444p
```

`yuv444p` stores full colour detail for every pixel. It's technically superior — and **most players, phones, and browsers cannot decode it.** The file is valid, plays perfectly in VLC on your machine, and shows a black screen on an iPhone.

The fix is one flag:

```bash
ffmpeg -y -f lavfi -i "testsrc=..." -c:v libx264 -pix_fmt yuv420p sample.mp4
```

**Output (real run):**
```
  with -pix_fmt yuv420p: yuv420p
```

> ⚠️ **Always pass `-pix_fmt yuv420p` when encoding H.264 for delivery.** ffmpeg preserves the input's pixel format by default, which is correct behaviour for an archival tool and wrong for a publishing pipeline. When someone reports "the video is black on my phone but fine on my laptop", check `pix_fmt` first — it's the answer more often than any other single field.

The reason it works this way: `yuv420p` throws away three-quarters of the colour resolution (keeping full brightness detail, which is what eyes actually notice). Decades of hardware decoders were built assuming it, so it's the only format guaranteed to work everywhere.

---

## Bitrate, resolution, frame rate

Three numbers that describe the video, often confused:

- **Resolution** — pixels per frame (1920×1080). More pixels need more bits.
- **Frame rate** — frames per second (25, 30, 60). Doubling it roughly doubles the data.
- **Bitrate** — bits per second of playback. **This is what determines file size**: `size ≈ bitrate × duration`.

Our sample probes as:

**Output (real run):**
```
duration=10.000000  size=159525  bit_rate=127620
```

127,620 bits/s × 10 s ÷ 8 = 159,525 bytes. The arithmetic closes exactly — bitrate is not an abstraction, it's the file size.

> **Tip:** Resolution and bitrate must move together. Encoding 4K at 500 kbps produces a smeared mess, and encoding 480p at 20 Mbps wastes bandwidth on detail that isn't there. [05-1](../05_encoding/01_codecs_and_crf.md) shows the better approach — target a *quality* level with CRF and let the encoder choose the bitrate.

---

## Recap & next

- ✅ **Container ≠ codec.** The box and the language inside it are independent choices.
- ✅ **Remuxing is ~instant** (8× faster here, and it scales); transcoding touches every frame.
- ✅ **MP4 + H.264 + AAC** for anything you deliver. MKV for work in progress.
- ✅ H.265/VP9/AV1 are smaller but less supported — a video that won't play is a bug, not an optimisation.
- ✅ **Always `-pix_fmt yuv420p`** for H.264 delivery, or it may be unplayable on phones despite being a valid file.
- ✅ `size ≈ bitrate × duration` — bitrate *is* file size.
- ✅ Self-check: a client sends a `.mov` that won't play in a browser. What are the two separate things that could be wrong?

→ Next: **[01-3 · Inspecting with ffprobe](03_inspecting_with_ffprobe.md)**

## Exercises

1. Remux `sample.mp4` to `.mkv` and confirm the video codec is unchanged.

<details>
<summary>Solution</summary>

```bash
ffmpeg -y -i sample.mp4 -c copy out.mkv
ffprobe -v error -select_streams v -show_entries stream=codec_name -of csv=p=0 out.mkv
# h264
```
Same `h264` stream, different container, no quality loss possible — nothing was decoded.
</details>

2. A colleague's H.264 MP4 plays on their Linux desktop but shows a black screen on iOS. Which field do you check first, and what do you expect to find?

<details>
<summary>Solution</summary>

`pix_fmt`, and you expect `yuv444p` (or `yuv422p`). Desktop players decode in software and handle it; iOS uses a hardware decoder that only supports `yuv420p`. Fix: re-encode with `-pix_fmt yuv420p`. Note this *does* require a real transcode — the pixel format is part of the encoded data, so `-c copy` can't change it.
</details>
