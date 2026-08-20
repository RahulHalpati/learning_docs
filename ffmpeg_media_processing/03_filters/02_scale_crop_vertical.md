# 03-2 · Scale, crop & vertical video

> **Level:** Intermediate · **Prerequisites:** [03-1 · Filtergraph syntax](01_filtergraphs.md)
> **Time:** 50 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2

## Why this matters

Short-form video is vertical. Almost all source footage is horizontal. Converting between them is the single most-requested operation in any modern video tool, and there are three legitimate ways to do it that produce visibly different results.

Getting there first requires `scale` and `crop`, which have a trap each.

---

## Scaling

```bash
ffmpeg -y -i sample.mp4 -vf "scale=1280:720" out.mp4
```

Fixed dimensions ignore the source aspect ratio and will stretch a 4:3 source into 16:9. Almost always you want one dimension computed:

```bash
ffmpeg -y -i sample.mp4 -vf "scale=320:-2" -an s1.mp4
ffmpeg -y -i sample.mp4 -vf "scale=-2:480" -an s2.mp4
```

**Output (real run, from 640×360):**
```
  scale=320:-2  -> 320x180
  scale=-2:480  -> 854x480
```

| Value | Meaning |
|-------|---------|
| `-1` | compute from the other dimension, preserving aspect |
| `-2` | same, **rounded to an even number** |
| `iw`, `ih` | input width/height — `scale=iw/2:ih/2` halves it |

### Why `-2` and not `-1`

```bash
ffmpeg -y -i sample.mp4 -vf "scale=321:-1" -an s3.mp4
```

**Output (real run):**
```
[libx264 @ 0x5ca6c2040a00] width not divisible by 2 (321x181)
Error initializing output stream 0:0 -- Error while opening encoder for output stream #0:0
```

H.264's `yuv420p` stores colour at half resolution in each direction, so **both dimensions must be even**. `-1` computes the mathematically correct height and hands the encoder an odd number, which it refuses.

> ⚠️ **Use `-2`, never `-1`, when scaling to an arbitrary size.** It's the same calculation rounded to an even number, and it costs you at most one pixel. `-1` works fine on your test file with round dimensions and fails on the first user upload with an odd aspect ratio — a failure that only appears in production.

### Don't upscale

Scaling 480p to 1080p makes a bigger file containing no additional detail — just a softer version of the same image. To resize *only when the source is large enough*:

```bash
-vf "scale='min(1920,iw)':-2"
```

The quotes matter here: `min(1920,iw)` contains a comma, which would otherwise be parsed as a filter separator ([03-1](01_filtergraphs.md)).

---

## Cropping

```
crop=WIDTH:HEIGHT:X:Y
```

X/Y default to centred, which is usually what you want:

```bash
ffmpeg -y -i sample.mp4 -vf "crop=320:180" out.mp4          # centred
ffmpeg -y -i sample.mp4 -vf "crop=320:180:0:0" out.mp4      # top-left
ffmpeg -y -i sample.mp4 -vf "crop=iw:ih/2:0:0" out.mp4      # top half
```

### Finding letterbox bars automatically

`cropdetect` analyses frames and reports the content rectangle:

```bash
ffmpeg -i letterboxed.mp4 -vf cropdetect=24:16:0 -frames:v 30 -f null -
```

**Output (real run, on a 640×360 video padded to 640×480):**
```
crop=640:352:0:64
```

It found the content at y=64 with a height of 352 — the real content was 360 tall at y=60, so it cropped slightly conservatively into the dark edges of the test pattern. That's typical: cropdetect is a *suggestion* based on how dark the borders are.

Then apply it:

```bash
ffmpeg -y -i letterboxed.mp4 -vf "crop=640:352:0:64" out.mp4
```

> **Tip:** Run cropdetect over frames from the *middle* of the video, not the start. Opening titles are often on a black background, and cropdetect will happily conclude the entire frame is a border. `-ss 60 -frames:v 100` samples somewhere real.

---

## Landscape → vertical: three strategies

All three produce 1080×1920. They look completely different.

**Output (real run — all three verified):**
```
  crop+scale       -> 1080x1920
  scale+pad(bars)  -> 1080x1920
  blurred backdrop -> 1080x1920
```

### 1. Centre crop — fills the frame, loses the sides

```bash
ffmpeg -y -i sample.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" -c:a copy out.mp4
```

`crop=ih*9/16:ih` takes a full-height slice as wide as a 9:16 rectangle would be, then scales it up. **From 16:9 you keep about 32% of the width** — everything at the sides is gone.

Best for talking heads centred in frame. Catastrophic for two people sitting apart, or anything where the subject drifts.

### 2. Letterbox — keeps everything, wastes space

```bash
ffmpeg -y -i sample.mp4 -vf "scale=1080:-2,pad=1080:1920:0:(oh-ih)/2:black" -c:a copy out.mp4
```

`pad=W:H:X:Y` grows the canvas; `(oh-ih)/2` centres the video vertically in it. Nothing is lost, but roughly half the screen is black bars, which reads as lazy on social platforms and measurably hurts retention.

### 3. Blurred backdrop — keeps everything, fills the frame

```bash
ffmpeg -y -i sample.mp4 -filter_complex \
  "[0:v]scale=1080:1920,boxblur=40[bg];\
   [0:v]scale=1080:-2[fg];\
   [bg][fg]overlay=(W-w)/2:(H-h)/2" -c:a copy out.mp4
```

The source twice: stretched and blurred as a background, natural-aspect on top. This is what CapCut, Instagram, and every other app do by default, because it loses nothing and fills the screen.

| Strategy | Loses content | Fills frame | Cost |
|----------|--------------|-------------|------|
| Centre crop | **yes, ~68% of width** | yes | cheap |
| Letterbox | no | no | cheap |
| Blurred backdrop | no | yes | ~2× (encodes two scaled copies) |

The capstone uses the centre crop for simplicity and honesty about its limits:

```python
def to_vertical(src, dst, *, width=1080, height=1920):
    vf = f"crop=ih*{width}/{height}:ih,scale={width}:{height}"
    ffmpeg(["-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", "23",
            "-c:a", "copy", str(dst)])
```

Note `-c:a copy` — cropping cannot affect audio, so re-encoding it would be pure loss ([02-1](../02_core_operations/01_converting.md)).

> ⚠️ **The naive centre crop is the weakest link in an automated pipeline.** It assumes the subject is centred, and when they aren't you get a clip of someone's shoulder. The real fix is subject tracking — detect faces per frame, smooth the path, and drive the crop's X position from it. That's a genuine upgrade to build on top of this course ([the capstone README](../99_project_mediakit/README.md) sketches it), not a prerequisite for a working MVP.

---

## Recap & next

- ✅ **`scale=W:-2`** preserves aspect and guarantees an even dimension; `-1` produces the real *"width not divisible by 2"* encoder failure.
- ✅ Don't upscale — `scale='min(1920,iw)':-2` resizes only when it helps.
- ✅ `crop=W:H:X:Y` centres by default; `cropdetect` finds letterbox bars (sample the **middle** of the video).
- ✅ Three ways to go vertical: **centre crop** (loses ~68% of width), **letterbox** (black bars), **blurred backdrop** (the app-standard look, ~2× cost).
- ✅ Always `-c:a copy` when only the video changes.
- ✅ **Naive centre crop is the weak link** in automation; subject tracking is the upgrade.
- ✅ Self-check: a user uploads 1920×1080 footage of two people at opposite edges. Which strategy, and why not the others?

→ Next: **[03-3 · Text & overlays](03_drawtext_overlays.md)**

## Exercises

1. Make a 9:16 version of `sample.mp4` using the blurred-backdrop approach and confirm the dimensions.

<details>
<summary>Solution</summary>

```bash
ffmpeg -y -i sample.mp4 -filter_complex \
  "[0:v]scale=1080:1920,boxblur=40[bg];[0:v]scale=1080:-2[fg];\
   [bg][fg]overlay=(W-w)/2:(H-h)/2" -c:a copy out.mp4
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 out.mp4
# 1080x1920
```
The background is deliberately stretched out of aspect — it's blurred beyond recognition, so distortion doesn't matter and filling the frame does.
</details>

2. Write a crop that takes the **right-hand** 9:16 slice instead of the centre.

<details>
<summary>Solution</summary>

```bash
-vf "crop=ih*9/16:ih:iw-ih*9/16:0,scale=1080:1920"
```
The X offset `iw-ih*9/16` puts the crop window's left edge exactly one window-width from the right edge. Written with expressions rather than numbers, it works on any input resolution — which is the whole reason filter expressions exist.
</details>
