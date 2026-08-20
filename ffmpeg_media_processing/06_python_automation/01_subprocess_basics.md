# 06-1 · Running ffmpeg from Python

> **Level:** Intermediate · **Prerequisites:** [05 · Encoding & quality](../05_encoding/README.md)
> **Time:** 45 min · **Verified:** 2026-08-07 · Python 3.10, ffmpeg 4.4.2

## Why this matters

There are Python wrappers for ffmpeg. You'll still end up reading their source when a command fails in a way they didn't anticipate, because they're all thin layers over the same command line. Calling `subprocess` directly is about 40 lines, has no dependency, and means you're debugging *your* code rather than someone else's abstraction.

The 40 lines do need to be right, though. Here's what goes into them.

---

## The naive version and everything wrong with it

```python
# don't do this
import os
os.system(f"ffmpeg -i {src} -c:v libx264 {dst}")
```

Four separate bugs:

1. **Shell injection.** A filename containing `; rm -rf ~` executes it. This is a real attack surface the moment filenames come from users.
2. **Filenames with spaces break** — `my video.mp4` becomes two arguments.
3. **No error detection.** `os.system` returns a status nobody checks.
4. **No error message.** ffmpeg's explanation goes to the terminal, not your logs.

---

## The correct version

```python
def run(args: list[str], *, binary: str = "ffmpeg") -> str:
    cmd = [_which(binary), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(
            f"{binary} failed (exit {proc.returncode})\n"
            f"command: {' '.join(cmd)}\n\n{proc.stderr.strip()}"
        )
    return proc.stdout
```

What each decision buys:

| Decision | Why |
|----------|-----|
| **list of args, no `shell=True`** | no shell, therefore no injection, and spaces just work |
| `capture_output=True` | stderr is captured, not lost to the console |
| `text=True` | strings, not bytes |
| **check `returncode`** | the only reliable success signal ([01-3](../01_foundations/03_inspecting_with_ffprobe.md)) |
| **stderr in the exception** | ffmpeg already told you what's wrong — pass it on |
| **command in the exception** | you can paste it into a terminal to reproduce |

> ⚠️ **Never use `shell=True` with user-controlled filenames.** Not for convenience, not "just for this script". A list of arguments is passed to `execve` directly with no shell involved, which makes injection structurally impossible rather than something you have to remember to escape.

### Errors you can act on

```python
def test_failure_raises_with_ffmpeg_stderr(tmp_path):
    with pytest.raises(FFmpegError) as exc:
        probe(tmp_path / "does_not_exist.mp4")
    assert "No such file" in str(exc.value)
```

The difference in practice:

```
FFmpegError: ffprobe failed (exit 1)
command: /usr/bin/ffprobe -v error -print_format json -show_format -show_streams /tmp/x.mp4

/tmp/x.mp4: No such file or directory
```

versus `CalledProcessError: Command '[...]' returned non-zero exit status 1.` One tells you what happened; the other tells you that something happened.

---

## Checking ffmpeg exists

```python
def _which(binary: str) -> str:
    exe = shutil.which(binary)
    if exe is None:
        raise FFmpegError(
            f"{binary} not found on PATH. Install it: "
            "`sudo apt install ffmpeg` (Debian/Ubuntu) or `brew install ffmpeg` (macOS)."
        )
    return exe
```

`shutil.which` is stdlib and cross-platform. Without this check the failure is `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'` — which reads like *your input file* is missing and sends people looking in the wrong place entirely.

---

## Sane defaults

```python
def ffmpeg(args: list[str], *, overwrite: bool = True) -> str:
    base = ["-hide_banner", "-loglevel", "error"]
    if overwrite:
        base.append("-y")
    return run([*base, *args])
```

`-y` matters more than it looks. Without it, ffmpeg prompts on an existing output file and waits on stdin — **in a background worker that's a job hung forever**, with no error and no timeout, holding a slot in your queue.

`-loglevel error` makes silence mean success, which makes the error path clean: anything in stderr is a real problem.

---

## Building commands

Keep them as lists and let each option be its own element:

```python
args = ["-i", str(src), "-vn", "-ar", str(rate)]
if mono:
    args += ["-ac", "1"]
args += ["-c:a", "pcm_s16le", str(dst)]
```

Note `str()` on every path — `subprocess` accepts `Path` objects, but building f-strings from them elsewhere in the chain will produce `PosixPath('/x')` in the middle of a command string. Converting at the boundary avoids a class of bug that's obvious in hindsight and baffling in the moment.

> **Tip:** Filter strings are the one place you do interpolate, and therefore the one place escaping matters — see `_escape_filter_path` in [03-1](../03_filters/01_filtergraphs.md). The rule: **arguments go in the list, never in a formatted string; filtergraph internals get escaped explicitly.**

---

## Should you use a wrapper library?

| | `subprocess` | `ffmpeg-python` | PyAV |
|---|---|---|---|
| Dependency | none | one | one (compiles) |
| What you learn | ffmpeg | the wrapper's API | libav internals |
| Debugging | the command you wrote | wrapper → command → ffmpeg | C library errors |
| Frame-level access | no | no | **yes** |

`ffmpeg-python` builds the same command lines with a fluent API; when a graph is wrong you debug through an extra layer. **PyAV is genuinely different** — it binds the libraries directly, so you can process individual frames in Python without shelling out. That's what you'd want for per-frame face detection to drive subject-tracked cropping ([03-2](../03_filters/02_scale_crop_vertical.md)).

For everything this course does, `subprocess` is the right tool: no dependency, and the commands in your code are the commands in the documentation.

---

## Temporary files

Media pipelines generate intermediates. Clean them up even when things fail:

```python
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    wav = extract_audio(src, Path(tmp) / "audio.wav")
    cues = transcribe(wav)
# directory and contents removed, including on exception
```

> ⚠️ **Video intermediates are large.** A pipeline that leaks a 200 MB intermediate per job fills a worker's disk in a few hundred jobs, and the failure — `No space left on device` — surfaces far away from the code that caused it. `TemporaryDirectory` as a context manager handles the exception path for free; a `finally` block you have to remember to write does not.

---

## Recap & next

- ✅ **Never `shell=True`** with user filenames — pass a list of arguments and injection is structurally impossible.
- ✅ **Check `returncode` and put stderr in the exception.** ffmpeg already explained the failure.
- ✅ Include the **command** in the error so it can be reproduced by pasting.
- ✅ `shutil.which` first, or a missing ffmpeg looks like a missing input file.
- ✅ **`-y` always in code** — otherwise a background job hangs forever on a prompt.
- ✅ `str()` paths at the boundary; only filtergraph internals are interpolated, and those get escaped.
- ✅ `subprocess` over a wrapper — except **PyAV** when you need per-frame access.
- ✅ **`TemporaryDirectory` for intermediates**, or a worker fills its disk.
- ✅ Self-check: a job in your queue has been "running" for six hours with no CPU use. What's the most likely cause?

→ Next: **[06-2 · Progress & long jobs](02_progress_and_jobs.md)**

## Exercises

1. Write `safe_convert(src, dst)` that raises a clear error if the source has no video stream.

<details>
<summary>Solution</summary>

```python
def safe_convert(src, dst):
    info = probe(src)                      # raises FFmpegError if unreadable
    if not any(s["type"] == "video" for s in info["streams"]):
        raise ValueError(f"{src} has no video stream")
    ffmpeg(["-i", str(src), "-c:v", "libx264", "-crf", "23",
            "-pix_fmt", "yuv420p", "-c:a", "aac", str(dst)])
```
Probing first turns a confusing mid-encode ffmpeg error into a precise one, before you've spent any CPU — the same fail-fast argument as extracting audio explicitly in [02-4](../02_core_operations/04_extracting_audio.md).
</details>

2. Why does `run()` return `proc.stdout` when ffmpeg writes nothing useful to stdout?

<details>
<summary>Solution</summary>

Because the same function runs **ffprobe**, which writes its JSON to stdout. One code path handles both binaries: ffmpeg's stdout is empty and ignored, ffprobe's is the payload. Splitting them into two functions would duplicate the error handling, which is the part that actually matters.
</details>
