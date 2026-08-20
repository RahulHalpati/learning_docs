# 04-2 · Burning in captions

> **Level:** Intermediate · **Prerequisites:** [04-1 · Subtitle formats](01_subtitle_formats.md)
> **Time:** 40 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2

## Why this matters

Burned-in captions are what makes a clip work on a muted feed. This is the last step of the capstone pipeline and the one with the most fiddly details — filter escaping, style syntax, and a re-encode you can't avoid.

---

## The command

```bash
ffmpeg -y -i sample.mp4 \
  -vf "subtitles=subs.srt:force_style='FontSize=24,BorderStyle=3,MarginV=40,PrimaryColour=&H00FFFFFF'" \
  -c:a copy out.mp4
```

**Output (real run):**
```
  burned_srt.mp4: 61687 bytes
```

Three things to notice:

1. **`subtitles=` is a video filter**, so this is a full re-encode ([02-1](../02_core_operations/01_converting.md)). Unavoidable — you're changing pixels.
2. **`-c:a copy`** — subtitles don't touch audio.
3. `force_style` applies ASS styling to a plain SRT, which has no styling of its own.

---

## `force_style`

The values are ASS style fields ([04-1](01_subtitle_formats.md)), comma-separated inside single quotes:

| Setting | Effect |
|---------|--------|
| `FontName=DejaVu Sans` | typeface |
| `FontSize=24` | size (in the subtitle renderer's coordinate space) |
| `PrimaryColour=&H00FFFFFF` | text colour, `&HAABBGGRR` |
| `OutlineColour=&H00000000` | outline/box colour |
| `BorderStyle=1` | outline + shadow |
| `BorderStyle=3` | **opaque box** — best legibility |
| `Outline=2` | outline thickness |
| `Alignment=2` | 2 = bottom-centre, 5 = top-centre |
| `MarginV=40` | distance from the edge |
| `Bold=1` | bold |

The capstone's defaults:

```python
def burn_captions(src, srt, dst, *, font_size=24, margin_v=40):
    style = f"FontSize={font_size},MarginV={margin_v},PrimaryColour=&H00FFFFFF,BorderStyle=3"
    vf = f"subtitles={_escape_filter_path(srt)}:force_style='{style}'"
    ffmpeg(["-i", str(src), "-vf", vf, "-c:a", "copy", str(dst)])
    return Path(dst)
```

`BorderStyle=3` (opaque box) rather than an outline, because it stays readable over *any* footage. `MarginV=40` keeps captions clear of the platform UI that covers the bottom of a vertical video ([03-3](../03_filters/03_drawtext_overlays.md)).

> **Tip:** `FontSize` is relative to the subtitle renderer's assumed 384-pixel-tall canvas, not your video's actual height. The same value looks very different on a 1920-tall vertical video than on a 360p test clip — so tune it at your real output resolution, not on a small test file.

---

## The escaping problem

This is where burning captions actually goes wrong in production.

The subtitle path sits *inside* a filter argument, so it's parsed by the filtergraph parser before it's used as a path. `:` separates filter options and `,` separates filters — and both appear in real paths.

```python
def _escape_filter_path(path) -> str:
    p = str(path).replace("\\", "/")
    p = p.replace("'", r"\'").replace(":", r"\:").replace(",", r"\,")
    return f"'{p}'"
```

**Output (real run, from the test suite):**
```
"C:/a/b.srt"  ->  'C\:/a/b.srt'
"a,b.srt"     ->  'a\,b.srt'
```

> ⚠️ **This fails on Windows for everyone at least once.** `C:\Users\me\subs.srt` contains a drive-letter colon *and* backslashes, and the raw path produces the baffling error *"Unable to parse option value"* — which says nothing about paths. Normalise separators to `/` and escape the colon. The same bug hits Linux the moment a user uploads a file with a comma in its name.

---

## Two filters: `subtitles` vs `ass`

```bash
ffmpeg -y -i sample.mp4 -vf "subtitles=subs.srt" -c:a copy out.mp4    # SRT/VTT/ASS + force_style
ffmpeg -y -i sample.mp4 -vf "ass=subs.ass" -c:a copy out.mp4          # ASS only, styling from the file
```

**Output (real run):**
```
  burned_ass.mp4: 56982 bytes
  burned_srt.mp4: 61687 bytes
```

| | `subtitles` | `ass` |
|---|---|---|
| Input | SRT, VTT, ASS, embedded | ASS only |
| Styling | via `force_style` | from the file |
| Use when | you generate captions programmatically | a designer produced the ASS |

`subtitles` is the one you'll use — you're generating cues from a model, and `force_style` gives full control without writing ASS headers by hand.

---

## Burning captions from an embedded track

If the subtitles are already a stream inside the file:

```bash
ffmpeg -y -i soft.mp4 -vf "subtitles=soft.mp4:si=0" -c:a copy hard.mp4
```

The input to the filter is **the video file itself**, with `si=0` selecting the first subtitle stream. This is how you flatten a soft-subbed master into a social-ready upload.

---

## The full pipeline in context

The capstone chains this after cutting and reframing:

```python
clip = cut_clip(src, outdir / "clip.mp4", start, end)
clip = to_vertical(clip, outdir / "clip_vertical.mp4")
srt  = write_srt(split_long_cues(local), outdir / "captions.srt")
final = burn_captions(clip, srt, outdir / "final.mp4")
```

**Output (real run):**
```
    44  captions.srt
 78910  clip.mp4
188427  clip_vertical.mp4
214024  final.mp4
```

> ⚠️ **That's three encodes for one clip** — cut, reframe, caption — so three generations of loss ([02-1](../02_core_operations/01_converting.md)). It's written this way because each intermediate is inspectable, which is worth a great deal while you're learning and debugging. **In production, chain the filters into one command instead:**
> ```bash
> ffmpeg -y -ss 12 -to 42 -i src.mp4 \
>   -vf "crop=ih*9/16:ih,scale=1080:1920,subtitles=captions.srt:force_style='...'" \
>   -c:v libx264 -crf 23 -c:a aac final.mp4
> ```
> One decode, one encode, roughly a third of the time and visibly better quality. That's the exercise below, and it's a real improvement to make to the toolkit.

### Rebasing cue timestamps

The subtlety people miss: cues from the transcript are in **source** time, but the clip starts at zero.

```python
local = [
    Cue(max(0.0, c.start - start), min(end - start, c.end - start), c.text)
    for c in cues
    if c.end > start and c.start < end
]
```

Subtract the clip's start, keep only cues that overlap the window, and clamp cues straddling the boundary. Skip this and your captions appear correctly timed for a video that no longer exists — they'll be offset by exactly the clip's start time, which looks like a mysterious sync bug.

---

## Recap & next

- ✅ Burning captions is a **filter**, therefore a re-encode. `-c:a copy` keeps the audio untouched.
- ✅ **`force_style`** applies ASS styling to plain SRT — `BorderStyle=3` (opaque box) reads over any footage.
- ✅ `MarginV=40` keeps captions above the platform UI.
- ✅ **Escape `:` `,` `'` in the subtitle path** — Windows drive letters and comma filenames both break it.
- ✅ `subtitles` for generated captions; `ass` when styling comes from the file.
- ✅ `subtitles=video.mp4:si=0` burns an embedded track.
- ✅ **Rebase cue timestamps** to the clip's start, or captions are offset by exactly the cut point.
- ✅ Chaining cut + reframe + caption into **one command** removes two generations of loss.
- ✅ Self-check: your captions are consistently 12 seconds late on every clip. What's the bug?

→ Next: **[05 · Encoding & quality](../05_encoding/README.md)**

## Exercises

1. Rewrite the three-step capstone pipeline as a single ffmpeg command.

<details>
<summary>Solution</summary>

```bash
ffmpeg -y -ss 12 -to 42 -i src.mp4 \
  -vf "crop=ih*9/16:ih,scale=1080:1920,subtitles=captions.srt:force_style='FontSize=24,BorderStyle=3,MarginV=40'" \
  -c:v libx264 -crf 23 -pix_fmt yuv420p -c:a aac -movflags +faststart final.mp4
```
One decode, one encode. The catch: the SRT must already be rebased to the clip's timeline, because the filter sees the *trimmed* stream starting at 0 — so you still generate the captions file first, you just don't render an intermediate video.
</details>

2. Your captions render at a sensible size on a 360p test clip and appear tiny on the 1080×1920 output. Why?

<details>
<summary>Solution</summary>

`FontSize` is interpreted against the subtitle renderer's own coordinate space (a 384px-tall canvas by default), which is then scaled to the video. The mismatch means a value tuned at one resolution doesn't transfer. Either tune at your real output resolution, or set `PlayResY` in an ASS file to pin the coordinate space explicitly — the second is the more robust fix if you render at several resolutions.
</details>
