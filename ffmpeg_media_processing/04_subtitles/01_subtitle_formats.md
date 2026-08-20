# 04-1 · Subtitle formats

> **Level:** Intermediate · **Prerequisites:** [03 · Filters](../03_filters/README.md)
> **Time:** 40 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2

## Why this matters

A speech-to-text model gives you `(start, end, text)`. Everything downstream — burning captions, an editable transcript, a subtitle track — needs that in a real format. There are two worth knowing, and one decision (soft vs hard) that determines whether your captions survive being uploaded.

---

## SRT — the one to default to

```
1
00:00:00,000 --> 00:00:02,000
Hello from ffmpeg

2
00:00:02,000 --> 00:00:05,000
Burned-in captions
```

The whole specification:

- A **1-based index**, incrementing, contiguous.
- A timestamp line: `HH:MM:SS,mmm --> HH:MM:SS,mmm`.
- One or more lines of text.
- **A blank line** between entries.

> ⚠️ **The milliseconds separator is a comma, not a period.** `00:00:01.500` is invalid SRT; it must be `00:00:01,500`. This is the single most common bug when generating SRT from code, because every other timestamp format in computing uses a period — and some players are lenient enough that it works in testing and fails on the platform you upload to.

Generating it correctly:

```python
def timestamp(seconds: float) -> str:
    if seconds < 0:
        raise ValueError(f"negative timestamp: {seconds}")
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
```

**Output (real run, from the test suite):**
```
0        -> 00:00:00,000
1.5      -> 00:00:01,500
61.25    -> 00:01:01,250
3661.007 -> 01:01:01,007
```

Integer millisecond arithmetic throughout — converting to a float and formatting would accumulate rounding error, and `59.9995` seconds must not become `00:01:00,000` in a file where cue N+1 starts at `00:00:59,999`.

> **Tip:** SRT has no styling. That's a feature — it's why every player, platform, and tool accepts it. Style at render time with `force_style` ([04-2](02_burning_captions.md)) and keep the transcript itself clean and portable.

---

## ASS — when you need styling

Advanced SubStation Alpha carries positioning, fonts, colours, and animation. Convert an SRT to see the structure:

```bash
ffmpeg -y -i subs.srt subs.ass
```

**Output (real run):**
```
Style: Default,Arial,16,&Hffffff,&Hffffff,&H0,&H0,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,0

[Events]
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,Hello from ffmpeg
Dialogue: 0,0:00:02.00,0:00:05.00,Default,,0,0,0,,Burned-in captions
```

The `Style:` line is positional — 23 comma-separated fields. The ones you'll actually change:

| Field | Meaning |
|-------|---------|
| 2 | font name |
| 3 | font size |
| 4 | primary colour, **`&HBBGGRR`** |
| 17 | border style: `1` = outline, `3` = opaque box |
| 19 | alignment: `2` = bottom-centre, `5` = top-centre |
| 22 | vertical margin |

> ⚠️ **ASS colours are `&HBBGGRR` — blue, green, red, backwards from HTML.** `&H0000FF` is **red**, not blue. Add an alpha byte in front for `&HAABBGGRR`, where `00` is fully opaque and `FF` fully transparent — also inverted from what you'd expect. Both of these will bite you exactly once, memorably.

Note the timestamps also differ: ASS uses `0:00:02.00` (one-digit hour, period, centiseconds) where SRT uses `00:00:02,000`. Don't hand-convert between them — `ffmpeg -i in.srt out.ass` does it correctly.

Use ASS when you need per-word karaoke highlighting, precise positioning, or multiple speaker styles. Use SRT for everything else.

---

## VTT — the web one

WebVTT is what HTML5 `<track>` elements consume. It's SRT with a header, **periods instead of commas**, and optional cue settings:

```
WEBVTT

00:00:00.000 --> 00:00:02.000
Hello from ffmpeg
```

```bash
ffmpeg -y -i subs.srt subs.vtt
```

You need it if you serve video in a browser player with selectable captions.

---

## Soft vs hard subtitles

**Soft** = a separate stream in the container. Toggleable, editable, selectable by language.

```bash
ffmpeg -y -i sample.mp4 -i subs.srt -c copy -c:s mov_text soft.mp4
```

**Output (real run):**
```
0,h264,video
1,aac,audio
2,mov_text,subtitle
```

Three streams, and the operation was a **stream copy** — instant, no quality loss. (`mov_text` is MP4's native subtitle codec; MKV takes `srt` directly.)

**Hard** = rendered into the pixels. Permanent, unremovable, universally visible.

| | Soft | Hard |
|---|---|---|
| Toggleable | yes | no |
| Editable later | yes | no |
| Cost to add | free (stream copy) | full re-encode |
| Survives social upload | **no** | yes |
| Styling control | player-dependent | exact |
| Accessibility tooling | yes | no |

> ⚠️ **Social platforms strip soft subtitles.** Upload an MP4 with a `mov_text` track to TikTok, Instagram, or YouTube Shorts and the captions are simply gone — the platform re-encodes and discards the stream. For short-form video, **burn them in.** This is the single most consequential fact in this section.

The practical answer is often both: burn them in for the delivered file, and keep the SRT alongside it for editing, search, translation, and re-rendering later. The capstone writes `captions.srt` next to `final.mp4` for exactly that reason.

---

## Splitting long cues

Whisper emits sentence-length segments. A 90-character line is unreadable on a phone, so the capstone re-flows them to the broadcast convention of ~42 characters:

```python
def split_long_cues(cues, *, max_chars=42):
    for cue in cues:
        words = cue.text.split()
        if len(cue.text) <= max_chars or not words:
            out.append(cue); continue
        # greedily pack words into lines...
        span = cue.end - cue.start
        cursor = cue.start
        for line in lines:
            share = span * (len(line.split()) / total_words)
            out.append(Cue(round(cursor, 3), round(cursor + share, 3), line))
            cursor += share
```

Time is divided by **word count**, not character count — words take roughly equal time to say regardless of length, so it tracks speech better. It's an approximation either way, and at 2-second cue lengths the error is imperceptible. The alternative is word-level timestamps from the model, which faster-whisper can provide (`word_timestamps=True`) at some cost in speed.

The test pins both the constraint and the boundaries:

```python
def test_split_long_cues_respects_max_chars():
    out = split_long_cues([Cue(0, 10, "word " * 30)], max_chars=42)
    assert len(out) > 1
    assert all(len(c.text) <= 42 for c in out)
    assert out[0].start == 0
    assert out[-1].end == pytest.approx(10, abs=0.01)
```

That last assertion matters: re-flowing must not drift the total timing.

---

## Recap & next

- ✅ **SRT** is the default: index, `HH:MM:SS,mmm --> ...`, text, blank line.
- ✅ **The millisecond separator is a comma.** Period is the most common generation bug.
- ✅ Build timestamps with **integer millisecond arithmetic** to avoid rounding drift.
- ✅ **ASS** adds styling; colours are `&HBBGGRR` (backwards) and alpha is inverted.
- ✅ **VTT** for HTML5 players.
- ✅ Soft subs are free to add and **stripped by every social platform** — burn in for short-form.
- ✅ Keep the SRT alongside the burned video for editing, search, and translation.
- ✅ Re-flow long cues to **~42 characters**, splitting time by word count.
- ✅ Self-check: you ship an MP4 with a `mov_text` track to a client uploading it to Instagram. What will they report?

→ Next: **[04-2 · Burning in captions](02_burning_captions.md)**

## Exercises

1. Write an SRT by hand with three cues and confirm ffmpeg accepts it by converting to ASS.

<details>
<summary>Solution</summary>

```bash
ffmpeg -y -i mine.srt mine.ass && echo OK
```
Conversion is a free validity check — ffmpeg's SRT parser will reject malformed timestamps or a missing blank line, so a successful convert means the file is well-formed. Cheaper than discovering it during a render.
</details>

2. `write_srt` is given cues where cue 2 starts before cue 1 ends. What happens, and should the function prevent it?

<details>
<summary>Solution</summary>

The file is written fine and most renderers display overlapping cues stacked or one replacing the other — messy but not fatal. Whether to prevent it is a design call: overlap is *legitimate* in ASS (two speakers positioned separately) but almost always a bug in generated SRT. A pragmatic middle ground is to clamp each cue's end to the next cue's start when writing SRT specifically, since it can't express simultaneity meaningfully anyway.
</details>
