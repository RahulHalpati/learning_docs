# 02-4 · Voiceover (TTS)

> **Level:** Beginner · **Time:** 25 min

The voiceover node speaks each segment's narration and — crucially — **measures
how long each one takes**, because those durations drive the slide timing later.

This is `voiceover` in [`nodes.py`](../99_project_faceless_studio/faceless_studio/nodes.py),
backed by `synth_narration` / `stitch_audio` in
[`media.py`](../99_project_faceless_studio/faceless_studio/media.py).

---

## The node

```python
from pathlib import Path
from . import media

def voiceover(state, *, workdir: Path) -> dict:
    audio_dir = Path(workdir) / "audio"
    segments = [dict(s) for s in state["segments"]]     # copy before mutating
    seg_paths = []
    for i, seg in enumerate(segments):
        path = audio_dir / f"seg_{i:02d}.wav"
        dur = media.synth_narration(seg["narration"], path)   # returns seconds
        seg["audio_path"] = str(path)
        seg["duration"] = dur
        seg_paths.append(str(path))

    full = Path(workdir) / "narration.wav"
    media.stitch_audio(seg_paths, full)
    return {"segments": segments, "audio_path": str(full), "log": ["voiceover"]}
```

It writes one `.wav` per segment, stitches them into one track, and enriches each
segment with `audio_path` + `duration`.

---

## The pluggable TTS layer (the clever bit)

The point of this course is that the pipeline **runs everywhere with nothing
installed**, yet upgrades to a real voice by touching *one function*. That lives in
`media.synth_narration`, chosen by `$STUDIO_TTS`:

```python
def synth_narration(text, out_path) -> float:
    engine = os.environ.get("STUDIO_TTS", "auto").lower()

    if engine in ("auto", "pyttsx3"):
        try:
            import pyttsx3
            tts = pyttsx3.init(); tts.save_to_file(text, str(out_path)); tts.runAndWait()
            if out_path.exists() and out_path.stat().st_size > 0:
                return _probe_duration(out_path)
        except Exception:
            if engine == "pyttsx3": raise

    if engine == "gtts":
        from gtts import gTTS
        mp3 = out_path.with_suffix(".mp3"); gTTS(text=text).save(str(mp3))
        _run([_ffmpeg(), "-y", "-i", str(mp3), str(out_path)])
        return _probe_duration(out_path)

    # fallback: a silent track sized to the estimated reading time
    duration = estimate_duration(text)
    _run([_ffmpeg(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
          "-t", str(duration), str(out_path)])
    return duration
```

| `STUDIO_TTS` | Voice | Needs | Online? |
|---|---|---|---|
| `auto` *(default)* | pyttsx3 if present, else **silent placeholder** | nothing | no |
| `pyttsx3` | OS voices | `pip install pyttsx3` | no |
| `gtts` | Google TTS | `pip install gTTS` | yes |
| `none` | always silent placeholder | nothing | no |

**Why a silent fallback isn't a cop-out:** the pipeline's job is *timing +
assembly*. A silent track sized to reading time (`estimate_duration`: words ÷ 150
wpm) makes every downstream node work correctly. Swap the engine and the slides,
assembly, and chapters are all still right — you just gain a voice.

### Real neural voices (the actual upgrade path)

For a channel you'd want a proper voice. Add one branch:

- **edge-tts** (free, Microsoft neural voices, online): `pip install edge-tts`,
  then `edge_tts.Communicate(text, "en-US-GuyNeural").save(mp3)`.
- **Piper** (offline, fast, local): download a voice model, shell out to the
  `piper` binary.
- **ElevenLabs** (best quality, paid API): their SDK, then read `_probe_duration`.

Each is ~5 lines added to `synth_narration`. **No other node changes.** That's the
payoff of isolating side-effects behind one function.

---

## Duration measurement

`_probe_duration` shells out to `ffprobe` to read the real length of whatever the
engine produced. For the silent branch we already know the length (we set it), so
we return it directly. Either way the segment gets an accurate `duration`, which
the assembler needs.

---

## Recap

- The voiceover node produces per-segment audio **and** measures each `duration`.
- `synth_narration` isolates *all* TTS choices behind one function and one env var.
- The **silent fallback** keeps timing/assembly correct with zero installs; real
  voices (edge-tts/Piper/ElevenLabs) drop in without touching any other node.

## Self-check

1. Why must the voiceover node run before the assembler, not in parallel with it?
2. What does the silent-track fallback still get *right*, and what does it lack?

<details>
<summary>Answers</summary>

1. The assembler needs each segment's **duration** to know how long to show its
   slide, and durations are produced by the voiceover node.
2. It gets **timing and assembly** right (correct-length video, correct chapters);
   it just has no actual spoken voice yet.

</details>

---

**Next → [02-5 · Visuals](05_visuals.md)**
