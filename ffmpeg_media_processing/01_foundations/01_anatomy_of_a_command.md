# 01-1 · Anatomy of an ffmpeg command

> **Level:** Beginner · **Prerequisites:** [00 · Introduction](../00_introduction.md)
> **Time:** 40 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2

## Why this matters

ffmpeg has over 400 command-line options and a manual that reads like a specification. People cope by copy-pasting commands from Stack Overflow without understanding them, which works right up until it doesn't — and then there's no way to debug it.

There is a grammar underneath, and it's small. Learn it and unfamiliar commands become readable.

---

## The grammar

```
ffmpeg [global options] [input options] -i INPUT [output options] OUTPUT
```

The critical rule: **options apply to the file that comes after them.** ffmpeg is positional, not a flag soup. An option written before `-i` configures the *input*; the same option after `-i` configures the *output*.

```bash
ffmpeg -y -ss 5 -i sample.mp4 -t 3 -c:v libx264 out.mp4
#      │  │            │       │     └─ output option: encode video with libx264
#      │  │            │       └─ output option: stop after 3 seconds
#      │  │            └─ THE INPUT
#      │  └─ input option: start reading at 5s
#      └─ global option: overwrite without asking
```

Read that as a sentence: *overwrite freely; open sample.mp4 starting at 5 seconds; write 3 seconds of it, encoded with libx264, to out.mp4.*

> **Analogy:** ffmpeg options are like adjectives in a sentence — they modify the noun that follows. `-ss 5 -i in.mp4` is "the input, seeked to 5s". `-i in.mp4 -ss 5` is "the output, starting from 5s of decoded material". Same words, different meaning.

---

## The four options you'll use constantly

### `-i` — input

Repeatable. Each `-i` adds an input, numbered from 0:

```bash
ffmpeg -i video.mp4 -i music.mp3 ...     # input 0 and input 1
```

### `-c` — codec

`-c:v` for video, `-c:a` for audio, `-c` for both. The magic value is `copy`:

```bash
-c:v libx264      # encode video as H.264
-c:a aac          # encode audio as AAC
-c copy           # don't encode anything — copy the streams as-is
```

### `-y` / `-n` — overwrite policy

Without either, ffmpeg **prompts** when the output exists:

```
File 'out.mp4' already exists. Overwrite? [y/N]
```

In a script this hangs forever waiting for stdin. **Always pass `-y` from code** — [06-1](../06_python_automation/01_subprocess_basics.md) bakes it into the toolkit for exactly this reason.

### `-hide_banner -loglevel error` — quiet down

By default ffmpeg prints its build configuration and a progress line to stderr on every run. For scripting:

```bash
ffmpeg -hide_banner -loglevel error -y -i sample.mp4 -c copy out.mkv
```

**Output (real run):**
```

```

Silence means success. That's the goal for automated use — [06-1](../06_python_automation/01_subprocess_basics.md) shows why suppressing output makes error handling *easier*, not harder.

| Level | Shows |
|-------|-------|
| `quiet` | nothing at all |
| `error` | only real failures ← **use this in scripts** |
| `warning` | failures + warnings |
| `info` | the default: banner, stream info, progress |
| `verbose` / `debug` | when you're genuinely stuck |

---

## Order matters: the `-ss` case

`-ss` (seek) is the classic example of position changing behaviour:

```bash
ffmpeg -ss 8 -i sample.mp4 -t 2 -c copy before.mp4     # input seek
ffmpeg -i sample.mp4 -ss 8 -t 2 -c copy after.mp4      # output seek
```

- **Input seek** (`-ss` before `-i`): ffmpeg jumps to roughly that position in the file, then starts reading. Fast — it doesn't process what it skips.
- **Output seek** (`-ss` after `-i`): ffmpeg decodes from the beginning and discards everything before the mark. Slower, but historically more precise.

**Output (real run, 10-second file):**
```
  -ss BEFORE -i (fast seek):  0.05s
  -ss AFTER  -i (decode all): 0.05s
```

Identical — because there's nothing meaningful to skip in a 10-second file. **The difference only appears at scale**: seeking to 45 minutes into a 2-hour recording, input seek is near-instant while output seek decodes 45 minutes of video first.

> **Tip:** Modern ffmpeg (4.x+) made input seek accurate for most cases, so `-ss` before `-i` is the right default. The remaining accuracy caveat is about keyframes, not seek position, and it's covered in [02-2](../02_core_operations/02_trimming_and_cutting.md).

---

## Selecting streams with `-map`

A file's streams are numbered. Ours:

**Output (real run, `ffprobe -show_entries stream=index,codec_type,codec_name`):**
```
0,h264,video
1,aac,audio
```

Referenced as `input:stream` — `0:0` is the video, `0:1` the audio. Type shorthands are easier: `0:v` (first video stream of input 0), `0:a` (first audio stream).

Without `-map`, ffmpeg picks *one stream of each type* automatically — the "best" one by its own heuristic. That's usually right, and silently wrong when a file has multiple audio tracks (dubs) or subtitle streams. Be explicit when it matters:

```bash
# take video from input 0, audio from input 1 — replace a soundtrack
ffmpeg -i video.mp4 -i music.mp3 -map 0:v -map 1:a -c:v copy -c:a aac out.mp4

# drop audio entirely
ffmpeg -i sample.mp4 -map 0:v -c copy silent.mp4
```

> ⚠️ **The moment you use `-map` once, automatic selection is off for the entire command.** `-map 0:v` alone gives you a video-only file — if you wanted the audio too, you must also write `-map 0:a`. This surprises everyone once; the symptom is a perfectly good video with no sound.

`-vn` (no video) and `-an` (no audio) are the quick versions when you're dropping a whole type — [02-4](../02_core_operations/04_extracting_audio.md) uses `-vn` for exactly this.

---

## Reading a real command

Here's one from the capstone. You should now be able to read every part:

```bash
ffmpeg -hide_banner -loglevel error -y \
  -i talk.mp4 \
  -vf "crop=ih*1080/1920:ih,scale=1080:1920" \
  -c:v libx264 -crf 23 \
  -c:a copy \
  vertical.mp4
```

*Quietly, overwriting: open talk.mp4; crop it to a 9:16 slice of its own height then scale to 1080×1920; encode the video as H.264 at quality 23; copy the audio untouched; write vertical.mp4.*

The audio is copied because cropping doesn't affect sound — **re-encoding audio here would cost time and quality for no benefit**. Spotting those is where the real speedups live.

---

## Recap & next

- ✅ The grammar is `ffmpeg [global] [input opts] -i IN [output opts] OUT` — **options modify the file that follows them**.
- ✅ `-c copy` skips encoding entirely; `-c:v` / `-c:a` target one stream type.
- ✅ **Always `-y` in scripts** — otherwise ffmpeg blocks on an overwrite prompt.
- ✅ `-hide_banner -loglevel error` makes silence mean success.
- ✅ `-ss` before `-i` seeks fast; the gain is invisible on short files and large on long ones.
- ✅ **Using `-map` once disables automatic stream selection for the whole command.**
- ✅ Self-check: `ffmpeg -i a.mp4 -map 0:v -c copy out.mp4` — what's missing from `out.mp4`?

→ Next: **[01-2 · Containers, codecs & streams](02_containers_and_codecs.md)**

## Exercises

1. Produce a copy of `sample.mp4` with no audio, without re-encoding the video.

<details>
<summary>Solution</summary>

```bash
ffmpeg -y -i sample.mp4 -an -c:v copy silent.mp4
```
`-an` drops audio; `-c:v copy` avoids re-encoding the video, so it runs in milliseconds. `-map 0:v -c copy` is equivalent — with the caveat from the warning above that once you use `-map`, you own *all* stream selection.
</details>

2. Why does `ffmpeg -i in.mp4 out.mp4` (no options at all) still produce a valid file?

<details>
<summary>Solution</summary>

ffmpeg infers everything: the container from the `.mp4` extension, then that container's *default* codecs (libx264 + aac), plus automatic stream selection. Convenient for one-off use, but you're accepting defaults for quality, pixel format, and bitrate that you didn't choose — the `yuv444p` trap in [01-2](02_containers_and_codecs.md) is exactly this biting you.
</details>
