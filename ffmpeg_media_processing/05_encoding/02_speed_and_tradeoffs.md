# 05-2 · Speed & tradeoffs

> **Level:** Intermediate → Advanced · **Prerequisites:** [05-1 · Codecs & CRF](01_codecs_and_crf.md)
> **Time:** 45 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2, libx264

## Why this matters

CRF sets quality. **Preset sets how hard the encoder works to achieve it.** In a product where a user is waiting for a job to finish, this is the knob that determines whether your service feels fast — and the conventional advice about it turns out to be only half true.

---

## Presets

Ten of them, from `ultrafast` to `placebo`. The theory: slower presets search harder for compression opportunities, producing smaller files at the same CRF.

Measured on a 1280×720 30 fps source at CRF 23:

**Output (real run):**
```
  ultrafast    0.32s   5585796 bytes
  veryfast     0.52s   2063529 bytes
  fast         0.82s   2330467 bytes
  medium       0.91s   2317699 bytes
  slow         1.39s   2234807 bytes
```

Two findings, and the second is not what the folklore says:

1. **`ultrafast` is dramatically worse — 2.7× larger** than everything else. It disables most of the encoder's tools. Avoid it for anything you deliver.
2. **From `veryfast` to `slow`, the sizes are within ~13% of each other** while the time grows 2.7×. On this content, `slow` bought nothing over `veryfast`.

> **Honest caveat:** this is synthetic content, and it favours the fast presets. `testsrc2` has clean edges and predictable motion, so the exhaustive searches in `slow` and `veryslow` find little the quick search missed. On real footage — grain, complex motion, scene cuts — the spread is wider, typically 10–20% smaller files from `medium` vs `veryfast`. The measurement here is real; treat it as a lower bound on the difference, and **benchmark your own content** rather than trusting either my numbers or the folklore.

That last point is the actual lesson. Preset advice is content-dependent, and you have the tools to measure it in about two minutes.

### Choosing

| Preset | Use for |
|--------|---------|
| `ultrafast` | live streaming, throwaway previews |
| **`veryfast`** | **user-facing jobs — the pragmatic default** |
| `medium` | libx264's default; batch work |
| `slow` | final masters, encode-once-serve-many |
| `veryslow`, `placebo` | rarely worth it |

The capstone uses `veryfast` for cutting because a user is waiting:

```python
args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac"]
```

> **Tip:** The economics flip depending on how many times a file will be watched. A video encoded once and served a million times (Netflix, YouTube) justifies `veryslow` — the bandwidth saving dwarfs the CPU cost. A preview a user is waiting on justifies `ultrafast`. Most application work sits between, at `veryfast` or `medium`.

---

## Resolution is the bigger lever

Presets and CRF are fine adjustments. Resolution is a blunt one, and it dominates:

| Change | Effect on encode time and size |
|--------|-------------------------------|
| 4K → 1080p | ~4× fewer pixels |
| 1080p → 720p | ~2.25× fewer pixels |
| 60 fps → 30 fps | ~2× fewer frames |

**Downscaling before encoding is almost always the biggest speedup available.** If your output is a 1080×1920 vertical clip, there is no reason to process 4K frames all the way through the pipeline — scale early, and every subsequent filter is cheaper too.

```bash
# scale first, so filters and the encoder both work on fewer pixels
ffmpeg -y -i 4k.mp4 -vf "scale=1080:-2,drawtext=..." -c:v libx264 -crf 23 out.mp4
```

Filter order within a chain matters for the same reason: `scale,crop` and `crop,scale` can produce identical output at very different costs.

---

## Threading

libx264 uses all cores by default. Limit it when you're running concurrent jobs:

```bash
ffmpeg -threads 4 -i in.mp4 ...
```

> ⚠️ **Don't run N unlimited ffmpeg jobs on an N-core machine.** Each tries to use every core, they thrash the scheduler and cache, and total throughput *drops* below running them sequentially. In a worker pool, divide cores by concurrency and set `-threads` explicitly. This is a real and frequently-missed production issue — it manifests as a queue that gets slower as you add workers.

---

## Hardware encoding

GPUs and CPU media engines have dedicated H.264 encoders:

```bash
-c:v h264_nvenc      # NVIDIA
-c:v h264_qsv        # Intel Quick Sync
-c:v h264_videotoolbox  # Apple
-c:v h264_vaapi      # Linux/AMD
```

Check what your build has:

```bash
ffmpeg -hide_banner -encoders | grep -i h264
```

| | Software (libx264) | Hardware |
|---|---|---|
| Speed | baseline | **5–20× faster** |
| Quality per bit | better | worse (~20–30% larger at equal quality) |
| CPU load | high | near zero |
| Availability | everywhere | hardware-specific |

**Use hardware encoding for**: live streaming, real-time preview, high-volume transcoding where storage is cheap. **Use software for**: final deliverables, anything quality-sensitive, and anything that must run identically everywhere.

> ⚠️ **Hardware encoders ignore or reinterpret `-crf`.** NVENC uses `-cq`, QSV uses `-global_quality`, and the values don't map to x264's scale. A pipeline that switches to hardware encoding without changing its quality flags will silently produce very different output — the flag isn't rejected, it's ignored.

---

## Speed vs your actual bottleneck

Before optimising the encoder, find out whether encoding is the problem. In a real pipeline the time often goes elsewhere:

| Stage | Typical cost |
|-------|-------------|
| Download / upload | often dominant |
| Audio extraction | ~instant |
| **Transcription** | **usually the slowest step** |
| Cutting | seconds |
| Filters + encode | seconds to minutes |

For the capstone's pipeline on CPU, transcription dwarfs everything else — a `base` faster-whisper model runs at roughly 5–10× realtime on a modern CPU, so a 10-minute video takes 1–2 minutes to transcribe and a few seconds to cut and render. **Optimising the encoder preset there would be optimising 5% of the runtime** ([06-4](../06_python_automation/04_transcription.md) covers the knobs that actually help).

Measure first. `time` on each stage is enough to find the answer.

---

## Recap & next

- ✅ **`ultrafast` is 2.7× larger** — avoid it for delivery.
- ✅ Measured here, **`veryfast` → `slow` differed by only ~13%** while costing 2.7× the time; real footage spreads wider, so **benchmark your own content**.
- ✅ `veryfast` for user-facing jobs, `medium` for batch, `slow` for encode-once-serve-many.
- ✅ **Resolution is a bigger lever than any preset** — scale early and every filter gets cheaper too.
- ✅ **Set `-threads` in worker pools**, or concurrent jobs thrash and throughput falls.
- ✅ Hardware encoding is 5–20× faster and ~25% less efficient; **it ignores `-crf`** and needs its own quality flags.
- ✅ **Find the real bottleneck first** — in an AI video pipeline it's usually transcription, not encoding.
- ✅ Self-check: you add a second worker to a 2-core box and throughput goes down. Why?

→ Next: **[06 · Python automation](../06_python_automation/README.md)**

## Exercises

1. Benchmark `veryfast` vs `medium` on your own footage and decide which to ship.

<details>
<summary>Solution</summary>

```bash
for p in veryfast medium; do
  /usr/bin/time -f "$p %es" ffmpeg -y -i real.mp4 -c:v libx264 -preset $p -crf 23 -an $p.mp4
  stat -c "  %s bytes" $p.mp4
done
```
The decision rule: if `medium` gives >10% smaller files and your jobs aren't latency-sensitive, take it. If a user is watching a progress bar, take `veryfast`. There is no universally correct answer, which is exactly why you measure.
</details>

2. Your worker box has 8 cores and you run 4 concurrent transcode jobs. What should `-threads` be, and why not leave it unset?

<details>
<summary>Solution</summary>

`-threads 2` — 8 cores ÷ 4 jobs. Left unset, each job tries to use all 8, so 32 threads compete for 8 cores. The context switching and cache contention make total throughput *worse* than 4 well-behaved jobs, and the symptom is confusing: adding workers appears to slow the queue down.
</details>
