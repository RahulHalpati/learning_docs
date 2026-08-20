# 06-4 · Transcription with faster-whisper

> **Level:** Intermediate → Advanced · **Prerequisites:** [02-4 · Extracting audio](../02_core_operations/04_extracting_audio.md), [06-1 · Running ffmpeg from Python](01_subprocess_basics.md)
> **Time:** 45 min · **Verified:** 2026-08-07 · pricing checked 2026-08-07

## Why this matters

Timestamped text is the key that unlocks everything else. Once you know *what* was said and *when*, you can generate captions, let an LLM pick highlights, make the video searchable, and cut on sentence boundaries instead of guessing.

This lesson answers the practical question first: **is the free option good enough?**

---

## faster-whisper is genuinely free

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) is **MIT-licensed**, and so are the Whisper models it runs. It's a reimplementation of OpenAI's Whisper on [CTranslate2](https://github.com/OpenNMT/CTranslate2), **up to 4× faster than `openai/whisper` at the same accuracy**, using less memory.

Free means free here, with no asterisk:

- MIT licence — commercial use permitted.
- Models download once (a few hundred MB to ~3 GB).
- **Runs entirely on your machine.** No API key, no network, no per-minute billing.
- Marginal cost per video is electricity.

The trade is that you supply the compute, and on CPU that's the slowest stage of your pipeline.

## Deepgram, for comparison

[Deepgram](https://deepgram.com/) Nova-3, as of **2026-08-07**:

| Mode | Price |
|------|-------|
| Batch (pre-recorded) | **$0.0043/min** (~$0.26/hour) |
| Streaming (real-time) | **$0.0077/min** (~$0.46/hour) |
| Free credit on signup | $200 (~45,000 minutes) |

Cheap in absolute terms. But run the numbers for a product: 1,000 hours of video a month is ~$260 batch, versus $0 and some CPU time.

## The recommendation

**Use faster-whisper.** It's free, private (audio never leaves your infrastructure — which also simplifies GDPR considerably), accurate, and has no per-request failure mode.

Choose Deepgram — or another API — when:

- You need **real-time streaming** transcription. This is the genuinely strong case; running streaming Whisper yourself is real engineering.
- You want **zero ops** and no model downloads in your deploy.
- You need **speaker diarisation** out of the box (pyannote does it locally but adds complexity).
- Your CPU budget is tighter than your cash budget.

For a self-funded MVP processing uploaded video, that's a clear win for faster-whisper. **That's the choice the capstone makes.**

---

## Using it

```bash
pip install faster-whisper==1.2.0
```

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio16k.wav", vad_filter=True)

for s in segments:
    print(f"[{s.start:.2f} -> {s.end:.2f}] {s.text}")
```

Three parameters carry most of the value:

| Parameter | Why |
|-----------|-----|
| `compute_type="int8"` | 8-bit quantisation — **the single biggest CPU speedup**, with negligible accuracy loss on small/base |
| `vad_filter=True` | voice-activity detection skips silence, so you don't transcribe dead air |
| `language="en"` | skips auto-detection when you already know |

> **Tip:** `segments` is a **generator** — transcription doesn't actually start until you iterate it. That surprises people timing the call: `model.transcribe(...)` returns instantly and the work happens in the `for` loop. It's also useful, since you can stream results to a UI as they arrive rather than waiting for the whole file.

### Model sizes

| Model | Size | CPU speed | Use for |
|-------|------|-----------|---------|
| `tiny` | ~75 MB | fastest | drafts, keyword spotting |
| **`base`** | ~150 MB | fast | **captions — a good default** |
| `small` | ~500 MB | moderate | better accuracy, still practical |
| `medium` | ~1.5 GB | slow | when accuracy matters |
| `large-v3` | ~3 GB | very slow on CPU | GPU work |

Start at `base` and move up only if the output isn't good enough. On CPU, `base` with `int8` runs at several times realtime; `large-v3` can be slower than realtime, meaning a 10-minute video takes more than 10 minutes.

---

## The pipeline integration

```python
def transcribe(media, *, model_size="base", language=None,
               compute_type="int8", workdir=None):
    if not is_available():
        return _placeholder_cues(media)

    from faster_whisper import WhisperModel

    wav = extract_audio(media, Path(workdir) / f"{media.stem}.16k.wav")
    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    segments, _info = model.transcribe(str(wav), language=language, vad_filter=True)
    return [Cue(float(s.start), float(s.end), s.text.strip()) for s in segments]
```

Three deliberate decisions:

1. **Extract audio explicitly first** ([02-4](../02_core_operations/04_extracting_audio.md)) — 16 kHz mono WAV is what the model converts to anyway, and doing it yourself means a broken upload fails in 0.1s with a clear ffmpeg error instead of 40 seconds into inference.
2. **Import inside the function.** faster-whisper is a heavy optional dependency; a top-level import makes the whole toolkit unimportable without it.
3. **Degrade gracefully.** Without the library, return real timings from silence detection with placeholder text:

```python
def _placeholder_cues(media):
    return [Cue(start, end, f"[segment {i}]")
            for i, (start, end) in enumerate(speech_segments(media), start=1)]
```

**Output (real run, without faster-whisper installed):**
```
note: faster-whisper not installed — using placeholder captions with real timings.
{
  "window": [0.0, 6.0],
  "cues": 1,
  "final": "/tmp/demo/out/final.mp4"
}
```

**Output (real run, `captions.srt`):**
```
1
00:00:00,000 --> 00:00:04,000
[segment 1]
```

The timings are genuine — they came from `silencedetect`. That keeps the cut/caption/render path fully exercisable in CI, on a machine with no models, in seconds. It's the same pattern the [LLM Evals](../../llm_evals_observability/) course uses: **a deterministic stub for the expensive probabilistic component**, so everything around it stays testable.

---

## Word-level timestamps

For karaoke-style captions where each word highlights as it's spoken:

```python
segments, _ = model.transcribe(wav, word_timestamps=True)
for segment in segments:
    for word in segment.words:
        print(f"{word.start:.2f}-{word.end:.2f}: {word.word}")
```

Slower, and it needs ASS rather than SRT to render ([04-1](../04_subtitles/01_subtitle_formats.md)). It also makes `split_long_cues`'s proportional time division unnecessary — you'd have real per-word timings instead of an estimate.

---

## Where the LLM goes

The capstone's `pick_highlight` is deliberately naive — the densest window of speech:

```python
def pick_highlight(cues, *, target=30.0):
    best, best_score = (cues[0].start, cues[0].start + target), -1.0
    for cue in cues:
        start, end = cue.start, cue.start + target
        score = sum(len(c.text) for c in cues if c.start >= start and c.end <= end)
        if score > best_score:
            best, best_score = (start, end), score
    return best
```

**This function is the seam.** Replacing it is what makes the pipeline "AI-powered":

```python
def pick_highlight_llm(cues, *, target=30.0):
    transcript = "\n".join(f"[{c.start:.1f}] {c.text}" for c in cues)
    response = llm.complete(
        f"Here is a transcript with timestamps:\n\n{transcript}\n\n"
        f"Identify the most engaging {target}-second span. "
        f"Return JSON: {{\"start\": float, \"end\": float, \"reason\": str}}"
    )
    picked = json.loads(response)
    return picked["start"], picked["end"]
```

Nothing else in the pipeline changes — cutting, reframing, and captioning don't care how the window was chosen. That's the payoff of building the media layer properly first: the AI part is a function you swap.

> **Tip:** "Most engaging" is a judgement, so you should measure whether the model is any good at it. Build a small set of videos with human-picked highlights and score the model's picks against them — that's precisely what the [LLM Evals & Observability](../../llm_evals_observability/) course sets up, and it's the difference between a demo and a product you can improve.

---

## Recap & next

- ✅ **faster-whisper is genuinely free** — MIT, models included, runs locally, ~4× faster than vanilla Whisper.
- ✅ Deepgram Nova-3 is **$0.0043/min batch, $0.0077/min streaming** — cheap per minute, real money at volume.
- ✅ **Use faster-whisper**; choose an API for **real-time streaming**, zero ops, or built-in diarisation.
- ✅ `compute_type="int8"` is the biggest CPU win; `vad_filter=True` skips silence; **`base` is a good default**.
- ✅ `segments` is a **generator** — work starts when you iterate.
- ✅ **Extract 16 kHz mono WAV yourself** so bad input fails fast and clearly.
- ✅ Import heavy deps **inside the function** and degrade to a **deterministic stub** so CI stays fast.
- ✅ **`pick_highlight` is the seam** where an LLM plugs in — and where you should measure it.
- ✅ Self-check: your transcription step takes longer than the video's duration. Which two settings do you check?

→ Next: **[99 · Capstone: mediakit](../99_project_mediakit/README.md)**

## Exercises

1. Install faster-whisper and run the full pipeline on a real video with speech.

<details>
<summary>Solution</summary>

```bash
pip install faster-whisper==1.2.0
python -m mediakit clip talk.mp4 out/ --target 30
```
The "faster-whisper not installed" note disappears and `captions.srt` contains real words instead of `[segment 1]`. Nothing else in the pipeline changes — which is the point of the fallback design.
</details>

2. Your product transcribes 500 hours a month. Compare faster-whisper on a rented CPU box against Deepgram batch.

<details>
<summary>Solution</summary>

Deepgram batch: `500 × 60 × $0.0043 ≈ $129/month`, zero ops.

faster-whisper: a mid-size cloud CPU instance runs ~$50–100/month and at ~5× realtime handles 500 hours in ~100 hours of compute — comfortably within a month on one box. So it's cheaper, but not dramatically, and you own the operational burden.

The honest conclusion: **at this volume the costs are close enough that price isn't the deciding factor.** Decide on privacy (audio never leaving your infrastructure), latency requirements, and whether you'd rather spend engineering time or money. The gap only becomes decisive at much higher volumes — or at much lower ones, where free really is free.
</details>

---

**Sources:** [faster-whisper (GitHub)](https://github.com/SYSTRAN/faster-whisper) · [Deepgram Nova-3 pricing](https://convertaudiototext.com/blog/deepgram-nova-3-explained) · [Deepgram pricing 2026](https://diyai.io/ai-tools/speech-to-text/deepgram-pricing-2026/)
