# 02-2 · Trimming & cutting

> **Level:** Beginner → Intermediate · **Prerequisites:** [02-1 · Converting & remuxing](01_converting.md)
> **Time:** 45 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2

## Why this matters

Cutting is the core operation of every video editing product. It's also where ffmpeg's most-hit trap lives: the fast way to cut produces a clip that is *approximately* what you asked for, and nothing warns you. If your product extracts a highlight starting at 1:23.4, "approximately" is a bug report.

---

## The two ways to cut

```bash
# Fast: copy the streams
ffmpeg -y -ss 2 -to 5 -i sample.mp4 -c copy fast.mp4

# Accurate: re-encode
ffmpeg -y -ss 2 -to 5 -i sample.mp4 -c:v libx264 -c:a aac exact.mp4
```

**Output (real run):**
```
  stream copy : 0.06s   duration 3.160000
  re-encode   : 0.27s   duration 3.000000
```

The copy is **4.5× faster and 0.16 seconds wrong.**

---

## Why the fast cut is wrong

[01-3](../01_foundations/03_inspecting_with_ffprobe.md) already showed the cause. Video frames come in two kinds:

- **Keyframes** (I-frames) — encoded standalone, decodable on their own.
- **Everything else** (P/B-frames) — store only the *difference* from neighbouring frames.

A decoder cannot start on a difference-frame; it has nothing to difference against. So when you stream-copy, ffmpeg cannot hand you a clip beginning at an arbitrary frame — it must start at a keyframe.

Even with keyframes every 2 seconds, the error persists:

```bash
ffmpeg -y -i sample.mp4 -c:v libx264 -g 50 -keyint_min 50 -sc_threshold 0 -c:a copy kf.mp4
ffprobe -v error -select_streams v:0 -skip_frame nokey -show_entries frame=pkt_pts_time -of csv=p=0 kf.mp4
```

**Output (real run — keyframe positions):**
```
0.000000  2.000000  4.000000  6.000000  8.000000
```

Now cut 3.0 → 6.0 (a 3-second clip starting *between* keyframes), video stream only so audio granularity isn't muddying the measurement:

**Output (real run, video stream duration):**
```
  copy   : 3.200000
  encode : 3.000000
```

Still off. **Adding keyframes reduces how far a copy-cut can drift, but never eliminates it** — unless your cut points happen to land exactly on keyframes, which in a real product they never do.

> ⚠️ **The failure mode is worse than "slightly wrong duration".** Depending on the player and how the cut landed, a copy-cut clip can open with a freeze, visible corruption, or silence while the decoder catches up — and the file still probes as valid. If a clip's first frame matters, re-encode.

---

## Choosing

| Use stream copy when | Use re-encode when |
|---------------------|--------------------|
| Chopping a long recording into rough chunks | The clip is a deliverable |
| Pre-processing before another encode | The first frame must be right |
| The cut point is flexible (± a second) | Exact duration matters |
| Speed dominates (thousands of files) | Any filter is applied anyway |

For an AI video tool that extracts highlights, it's **always re-encode**. That's why the capstone defaults to it:

```python
def cut_clip(src, dst, start, end, *, accurate=True):
    args = ["-ss", f"{start}", "-to", f"{end}", "-i", str(src)]
    if accurate:
        args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac"]
    else:
        args += ["-c", "copy"]
    ffmpeg([*args, str(dst)])
```

`-preset veryfast` is the deliberate compromise: cutting is on the critical path of a user-facing job, so trading a little compression efficiency for speed is the right call ([05-2](../05_encoding/02_speed_and_tradeoffs.md)).

And the difference is asserted in the test suite rather than merely claimed:

```python
def test_stream_copy_is_only_approximate(sample, tmp_path):
    fast = cut_clip(sample, tmp_path / "f.mp4", 2.0, 5.0, accurate=False)
    exact = cut_clip(sample, tmp_path / "e.mp4", 2.0, 5.0, accurate=True)
    assert abs(duration(exact) - 3.0) < abs(duration(fast) - 3.0)
```

---

## `-to` vs `-t`

Two ways to say when to stop, and mixing them up is a common off-by-N-seconds bug:

```bash
ffmpeg -y -ss 2 -to 5 -i sample.mp4 ...     # stop at absolute 5s  → 3s clip
ffmpeg -y -ss 2 -t 5  -i sample.mp4 ...     # run for 5s duration  → 5s clip
```

- **`-to`** = an end *timestamp*
- **`-t`** = a *duration*

> **Tip:** Prefer `-to` when you're working from transcript timestamps (a highlight runs from 65.2s to 94.8s) and `-t` when you have a target length ("give me 30 seconds"). Converting between them in your head is where the bug comes from — let the flag match the data you actually have.

---

## Time formats

All equivalent:

```bash
-ss 90            # seconds
-ss 00:01:30      # HH:MM:SS
-ss 00:01:30.500  # with milliseconds
-ss 1:30          # MM:SS
```

Plain seconds is best from code — it's what your transcript timestamps already are, with no formatting step to get wrong.

---

## Removing a section from the middle

There's no "delete this range" flag. You cut the parts you're keeping and join them ([02-3](03_concatenating.md)):

```bash
# remove 4s–8s from a 12s video
ffmpeg -y -ss 0 -to 4  -i talk.mp4 -c:v libx264 -c:a aac part1.mp4
ffmpeg -y -ss 8 -to 12 -i talk.mp4 -c:v libx264 -c:a aac part2.mp4
printf "file 'part1.mp4'\nfile 'part2.mp4'\n" > list.txt
ffmpeg -y -f concat -safe 0 -i list.txt -c copy out.mp4
```

**Output (real run):**
```
joined duration = 8.0s   (12s source, 4s removed)
```

Note the pattern: **re-encode the parts, copy the join.** The parts need accurate cuts; the concat step is just repackaging, so it costs nothing.

---

## Recap & next

- ✅ Stream copy is **4.5× faster and inexact**; re-encoding hits the timestamp precisely.
- ✅ The cause is **keyframes** — a copy can only start where a decoder can start.
- ✅ Adding keyframes (`-g 50`) shrinks the error but **does not remove it** (3.20s vs 3.00s here).
- ✅ A bad copy-cut can also produce a frozen or corrupt first frame — while still probing as valid.
- ✅ For deliverable clips, **always re-encode**; `-preset veryfast` keeps it responsive.
- ✅ **`-to` is a timestamp, `-t` is a duration.** Pick the one matching your data.
- ✅ Delete-from-the-middle = cut the keepers accurately, then concat with `-c copy`.
- ✅ Self-check: your highlight detector says the good bit starts at 47.3s. Which cut mode, and why?

→ Next: **[02-3 · Concatenating](03_concatenating.md)**

## Exercises

1. Extract seconds 4–7 of `sample.mp4` both ways and compare the actual durations.

<details>
<summary>Solution</summary>

```bash
ffmpeg -y -ss 4 -to 7 -i sample.mp4 -c copy a.mp4
ffmpeg -y -ss 4 -to 7 -i sample.mp4 -c:v libx264 -c:a aac b.mp4
for f in a.mp4 b.mp4; do ffprobe -v error -show_entries format=duration -of csv=p=0 $f; done
```
`b.mp4` will be 3.00s. `a.mp4` won't — the exact value depends on where the keyframes fell, which is precisely the problem: it's unpredictable from outside.
</details>

2. You need to cut 500 clips from a 4-hour recording for a rough review pass, then produce final versions of the 20 that get approved. What's the efficient strategy?

<details>
<summary>Solution</summary>

Stream-copy all 500 for the review pass — speed matters, ±1s doesn't, and you avoid 500 needless encodes. Then re-encode only the approved 20 from the **original** file (not from the copy-cut, which would add a generation of loss and inherit the imprecise boundaries). Cheap where quality is irrelevant, exact where it ships.
</details>
