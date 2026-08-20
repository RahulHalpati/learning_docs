# 05-1 · Codecs & CRF

> **Level:** Intermediate · **Prerequisites:** [02-1 · Converting & remuxing](../02_core_operations/01_converting.md)
> **Time:** 50 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2, libx264

## Why this matters

"How do I make the file smaller?" is the most common follow-up question in media work, and the usual answer — set a bitrate — is the wrong one. There's a better knob, and this lesson shows exactly what it costs you.

---

## Two ways to control size

| Mode | Flag | You specify | Encoder decides |
|------|------|-------------|-----------------|
| **Constant quality** | `-crf 23` | how good it looks | the bitrate |
| **Constant bitrate** | `-b:v 2M` | the bitrate | how good it looks |

CRF is right for almost everything. Bitrate targeting is for live streaming and hard delivery contracts, where a predictable data rate matters more than consistent quality.

The reason: **different content needs wildly different bitrates for the same visual quality.** A static slide needs almost nothing; a snowstorm needs a lot. CRF gives the encoder permission to spend bits where they're needed. Fixed bitrate wastes them on the slide and starves the snowstorm.

---

## What CRF actually costs

Measured on a 1280×720 30 fps source, `-preset medium`, PSNR against the lossless original:

**Output (real run):**
```
  crf=18    3557645 bytes   PSNR  49.70 dB
  crf=23    2317699 bytes   PSNR  44.52 dB
  crf=28    1121545 bytes   PSNR  39.72 dB
  crf=33     607973 bytes   PSNR  36.93 dB
  crf=40     406017 bytes   PSNR  34.50 dB
```

Read the shape of that, not the individual rows:

| Step | Size change | Quality change |
|------|-------------|----------------|
| 18 → 23 | **−35%** | −5.2 dB |
| 23 → 28 | **−52%** | −4.8 dB |
| 28 → 33 | −46% | −2.8 dB |
| 33 → 40 | −33% | −2.4 dB |

Every +5 CRF roughly **halves the file**. The quality cost per step is fairly steady in PSNR terms, but perceptually it isn't — the first steps down from 18 are nearly invisible, and by 33 you can see it.

> **Analogy:** CRF is JPEG quality for video, and inverted — **lower CRF means better quality**, the opposite of how most quality sliders work. `-crf 0` is mathematically lossless.

### Picking a value

| CRF | Use for |
|-----|---------|
| 0 | lossless — enormous, archival only |
| 15–18 | visually lossless; masters and intermediates |
| **19–23** | **high quality delivery — the default range** |
| 24–28 | good quality, noticeably smaller; social video |
| 29–35 | visible artefacts; previews, thumbnails, drafts |
| 36+ | bad |

**`-crf 23` is libx264's default and a genuinely good choice.** Start there, adjust only if you have a reason.

> **Tip:** The most valuable single move in the table above is **23 → 28: half the file size for a quality drop most viewers won't notice on a phone.** For social video that's usually the right trade. For a portfolio piece or a client master, stay at 20–23.

---

## The PSNR caveat

PSNR measures pixel-level difference against the original. It's objective, reproducible, and **not the same as how good something looks.** It over-penalises film grain (which the encoder is right to smooth) and under-penalises blocking in flat areas (which viewers notice immediately).

It's used here because it's measurable and honest about being a proxy. If you're tuning encoding seriously, look at **VMAF** — Netflix's perceptual metric, built for exactly this:

```bash
ffmpeg -i encoded.mp4 -i original.mp4 -lavfi libvmaf -f null -
```

(Requires an ffmpeg built with `--enable-libvmaf`; not present in the stock Ubuntu 4.4.2 build used here.)

And the real test remains: watch it, at the size and on the device your users will.

---

## Codec choice, revisited

[01-2](../01_foundations/02_containers_and_codecs.md) covered the landscape. The encoding-specific notes:

```bash
# H.264 — universal, the default
-c:v libx264 -crf 23 -pix_fmt yuv420p

# H.265 — ~50% smaller at the same quality, but slower and less supported
-c:v libx265 -crf 28 -tag:v hvc1

# VP9 — for WebM
-c:v libvpx-vp9 -crf 31 -b:v 0

# AV1 — best compression, slowest
-c:v libaom-av1 -crf 30 -b:v 0
```

Three traps in those lines:

- **CRF scales are not comparable across codecs.** x265's CRF 28 is roughly x264's CRF 23. Copying a number between codecs gives you a much worse or much bigger file than you expected.
- **`-tag:v hvc1`** is required for H.265 to play on Apple devices. Without it, Safari and QuickTime refuse a perfectly valid file.
- **VP9 and AV1 need `-b:v 0`** to enable true constant-quality mode. Without it, CRF acts as a *cap* on a bitrate-targeted encode and the results are poor — a genuinely surprising piece of API design.

---

## Audio bitrates

Far simpler, and rarely worth agonising over:

| Bitrate | Use |
|---------|-----|
| `-b:a 96k` | mono speech |
| `-b:a 128k` | **stereo speech / general — the default** |
| `-b:a 192k` | music |
| `-b:a 256k+` | diminishing returns for AAC |

Audio is typically 5–10% of a video file's size. Spending effort optimising it while the video is at CRF 18 is misallocated attention.

---

## Two-pass encoding

When you must hit a specific file size (an upload limit, a bandwidth contract):

```bash
ffmpeg -y -i in.mp4 -c:v libx264 -b:v 2M -pass 1 -an -f null /dev/null
ffmpeg -y -i in.mp4 -c:v libx264 -b:v 2M -pass 2 -c:a aac out.mp4
```

Pass 1 analyses the content's complexity; pass 2 distributes the bit budget accordingly — hard scenes get more, easy scenes get less. Better quality than single-pass at the same bitrate, at double the encoding time.

**Use it only when the size is a hard requirement.** If you just want "small and good", CRF is better and half the work.

To hit a target size, work backwards:

```
total_bitrate (bits/s) = target_size_bytes × 8 / duration_seconds
video_bitrate = total_bitrate − audio_bitrate
```

---

## The delivery command

Everything in the course so far, combined:

```bash
ffmpeg -y -i input.mp4 \
  -c:v libx264 -crf 23 -preset veryfast -pix_fmt yuv420p \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  output.mp4
```

| Flag | Lesson |
|------|--------|
| `-crf 23` | this lesson |
| `-preset veryfast` | [05-2](02_speed_and_tradeoffs.md) |
| `-pix_fmt yuv420p` | [01-2](../01_foundations/02_containers_and_codecs.md) — or it won't play on phones |
| `-b:a 128k` | this lesson |
| `-movflags +faststart` | [02-1](../02_core_operations/01_converting.md) — instant playback over HTTP |

If you remember one command from this course, that's the one.

---

## Recap & next

- ✅ **CRF (constant quality) beats bitrate targeting** for almost everything — it spends bits where content needs them.
- ✅ **Every +5 CRF roughly halves the file.** Measured: 3.56 MB → 2.32 MB → 1.12 MB → 608 KB → 406 KB.
- ✅ Lower CRF = better quality. **23 is the default and a good one**; 19–23 for delivery.
- ✅ **23 → 28 halves the size** for a drop most phone viewers won't see — usually the right social-video trade.
- ✅ PSNR is a **proxy**, not perception; VMAF is better, watching it is best.
- ✅ **CRF values aren't comparable across codecs** (x265 28 ≈ x264 23); H.265 needs `-tag:v hvc1`; VP9/AV1 need `-b:v 0`.
- ✅ Two-pass only when a **specific file size** is a hard requirement.
- ✅ Self-check: your 4K encode at `-b:v 2M` looks fine in the interview scenes and falls apart in the action scenes. What's the fix?

→ Next: **[05-2 · Speed & tradeoffs](02_speed_and_tradeoffs.md)**

## Exercises

1. Encode the same source at CRF 20 and CRF 30 and compare size and PSNR.

<details>
<summary>Solution</summary>

```bash
for crf in 20 30; do
  ffmpeg -y -i src.mp4 -c:v libx264 -crf $crf -an out$crf.mp4
  ffmpeg -i out$crf.mp4 -i src.mp4 -lavfi psnr -f null - 2>&1 | grep -o "average:[0-9.]*"
done
```
Expect roughly a 3–4× size difference. Then actually watch both full-screen — the point of the exercise is calibrating your own eye against the numbers, because the numbers alone won't tell you where *your* acceptable threshold is.
</details>

2. You need a 10-minute 1080p video under 100 MB. CRF or two-pass?

<details>
<summary>Solution</summary>

Two-pass, because the size is a hard constraint. Budget: `100 MB × 8 / 600 s ≈ 1.33 Mbps` total, minus 128k audio ≈ **1.2 Mbps video**.

The pragmatic alternative many people prefer: try `-crf 26` first and check the result. If it lands under 100 MB you get better quality than two-pass at the same size *and* you're done in one pass. Two-pass is the fallback when you can't afford to guess wrong.
</details>
