# 02-4 · Extracting audio

> **Level:** Beginner → Intermediate · **Prerequisites:** [02-1 · Converting & remuxing](01_converting.md)
> **Time:** 30 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2

## Why this matters

This is the first step of every AI video feature. Transcription, highlight detection, silence-based cutting, speaker diarisation, music removal — all of them start by pulling the audio out of the video. Getting the format right here makes the model step faster and cheaper; getting it wrong wastes both.

---

## The basic extraction

```bash
ffmpeg -y -i sample.mp4 -vn -c:a copy audio.m4a
```

`-vn` = no video. `-c:a copy` = don't re-encode the audio, just lift it out of the container.

**Output (real run):**
```
copied.m4a   94029 bytes
```

Instant and lossless. **This is the right choice when a human will listen to the result.** It's the wrong choice when a model will.

---

## The format speech-to-text actually wants

Whisper, faster-whisper, and essentially every other speech model resample their input to **16 kHz mono PCM** internally before doing anything else. Handing them anything else means they do a conversion you could have done for free.

```bash
ffmpeg -y -i sample.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le audio16k.wav
```

| Flag | Meaning | Why |
|------|---------|-----|
| `-vn` | drop video | you're not transcribing pixels |
| `-ac 1` | 1 audio channel (mono) | speech models mix to mono anyway; stereo is 2× the data for zero gain |
| `-ar 16000` | 16 kHz sample rate | speech tops out around 8 kHz; 16 kHz captures it (Nyquist) and nothing above |
| `-c:a pcm_s16le` | uncompressed 16-bit WAV | no decode step, no compression artefacts fed into the model |

**Output (real run):**
```
codec_name=pcm_s16le
sample_rate=16000
channels=1
```

### The size comparison

**Output (real run, same 10-second source):**
```
  raw44.wav      882766 bytes    # 44.1 kHz PCM
  raw16.wav      320328 bytes    # 16 kHz mono PCM  ← 2.76× smaller
  copied.m4a      94029 bytes    # AAC, stream-copied
  out.mp3         48592 bytes    # MP3 V2
```

The arithmetic is exact and worth internalising: **PCM size = sample_rate × bytes_per_sample × channels × seconds.** For 16 kHz mono 16-bit: `16000 × 2 × 1 × 10 = 320,000` bytes, plus a 328-byte WAV header. There's no guessing with uncompressed audio.

> **Tip:** Don't be tempted by the smaller MP3. For a *model*, uncompressed is better and the size difference is irrelevant — you're feeding a local process, not a network. For *storage*, keep the compressed version. Different jobs, different formats.

---

## Why not just feed it the MP4?

faster-whisper will accept the video file directly — it shells out to ffmpeg internally to do exactly what we just did. Doing it yourself buys three things:

1. **You control the parameters.** Explicit beats implicit when transcription quality is the product.
2. **You can reuse the WAV.** Silence detection ([06-3](../06_python_automation/03_analysis.md)), waveform display, and a second transcription pass all read the same file instead of re-extracting.
3. **It fails early and clearly.** A broken upload fails at a 0.1-second extraction step with a readable ffmpeg error, not 40 seconds into model inference with a stack trace from inside a library.

That third one matters most in a job queue. The capstone therefore extracts explicitly:

```python
def extract_audio(src, dst, *, rate=16000, mono=True):
    args = ["-i", str(src), "-vn", "-ar", str(rate)]
    if mono:
        args += ["-ac", "1"]
    args += ["-c:a", "pcm_s16le", str(dst)]
    ffmpeg(args)
    return Path(dst)
```

...and asserts the result rather than assuming it:

```python
def test_extract_audio_produces_16k_mono(sample, tmp_path):
    wav = extract_audio(sample, tmp_path / "a.wav")
    stream = probe(wav)["streams"][0]
    assert stream["codec"] == "pcm_s16le"
    assert stream["sample_rate"] == "16000"
    assert stream["channels"] == 1
```

---

## Other useful audio extractions

```bash
# MP3 for a podcast feed (V2 ≈ 190 kbps VBR, transparent for speech)
ffmpeg -y -i talk.mp4 -vn -c:a libmp3lame -q:a 2 talk.mp3

# a single channel from a stereo interview (each speaker on their own mic)
ffmpeg -y -i interview.mp4 -map_channel 0.1.0 left.wav

# normalise loudness to the broadcast standard (-16 LUFS is typical for podcasts)
ffmpeg -y -i talk.mp4 -vn -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a pcm_s16le norm.wav

# a waveform image, for a UI scrubber
ffmpeg -y -i talk.mp4 -filter_complex "showwavespic=s=1200x200:colors=white" -frames:v 1 wave.png
```

`loudnorm` is worth knowing about beyond transcription — inconsistent volume between clips is one of the most noticeable amateur-video tells, and it's a one-filter fix.

---

## Handling video with no audio

Screen recordings, generated animations, and silent uploads all exist. Extracting audio from them fails:

```
Output file #0 does not contain any stream
```

Check before you try:

```python
def has_audio(path) -> bool:
    return any(s["type"] == "audio" for s in probe(path)["streams"])
```

> ⚠️ **A silent video is not an error case in your product — it's a normal input.** Users upload screen recordings all the time. Branch on `has_audio()` and skip transcription rather than letting an ffmpeg failure bubble up as "processing failed", which tells the user nothing actionable.

---

## Recap & next

- ✅ `-vn -c:a copy` extracts audio losslessly and instantly — **for humans**.
- ✅ **For speech models: `-ac 1 -ar 16000 -c:a pcm_s16le`.** It's what they convert to anyway.
- ✅ 16 kHz mono PCM is **2.76× smaller** than 44.1 kHz, with no loss of speech information.
- ✅ `PCM size = rate × bytes × channels × seconds` — exact, no estimating.
- ✅ Extract explicitly rather than passing the MP4: control, reuse, and **fast clear failures**.
- ✅ `loudnorm` fixes inconsistent volume, the most audible amateur tell.
- ✅ **Check `has_audio()` first** — silent uploads are normal input, not an error.
- ✅ Self-check: why is uncompressed WAV the *better* choice for a model despite being 6× larger than MP3?

→ Next: **[03 · Filters](../03_filters/README.md)**

## Exercises

1. Extract 16 kHz mono WAV from `sample.mp4` and verify the file size matches the formula.

<details>
<summary>Solution</summary>

```bash
ffmpeg -y -i sample.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le a.wav
stat -c%s a.wav        # 320328
```
`16000 × 2 bytes × 1 channel × 10 s = 320,000`, plus a 328-byte WAV header. Uncompressed audio has no surprises — if the size is wrong, one of your parameters didn't apply, which makes this a quick sanity check for the whole command.
</details>

2. Write the check that decides whether to run transcription on an upload.

<details>
<summary>Solution</summary>

```python
if not has_audio(upload):
    return {"transcript": [], "note": "no audio track — captions skipped"}
```
Returning a structured "here's why there are no captions" beats raising, because the rest of the pipeline (cutting, reframing, thumbnails) still works fine on a silent video and the user should get that output rather than a failed job.
</details>
