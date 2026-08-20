"""Real ffmpeg, real files, real assertions. No mocks — the point is that the
commands work, and a mocked subprocess would prove nothing about that."""
from __future__ import annotations

import pytest

from mediakit import (
    Cue,
    FFmpegError,
    burn_captions,
    concat,
    cut_clip,
    detect_silence,
    duration,
    extract_audio,
    probe,
    speech_segments,
    split_long_cues,
    thumbnail,
    timestamp,
    to_vertical,
    write_srt,
)
from mediakit.ops import _escape_filter_path
from mediakit.pipeline import make_clip, pick_highlight


# ---------------------------------------------------------------- core

def test_probe_reports_streams_and_duration(sample):
    info = probe(sample)
    assert info["duration"] == pytest.approx(12.0, abs=0.2)
    kinds = {s["type"] for s in info["streams"]}
    assert kinds == {"video", "audio"}
    video = next(s for s in info["streams"] if s["type"] == "video")
    assert (video["width"], video["height"]) == (640, 360)


def test_failure_raises_with_ffmpeg_stderr(tmp_path):
    with pytest.raises(FFmpegError) as exc:
        probe(tmp_path / "does_not_exist.mp4")
    assert "No such file" in str(exc.value)


# ---------------------------------------------------------------- audio

def test_extract_audio_produces_16k_mono(sample, tmp_path):
    wav = extract_audio(sample, tmp_path / "a.wav")
    stream = probe(wav)["streams"][0]
    assert stream["codec"] == "pcm_s16le"
    assert stream["sample_rate"] == "16000"
    assert stream["channels"] == 1


# ---------------------------------------------------------------- cutting

def test_accurate_cut_hits_exact_duration(sample, tmp_path):
    clip = cut_clip(sample, tmp_path / "c.mp4", 2.0, 5.0)
    assert duration(clip) == pytest.approx(3.0, abs=0.05)


def test_stream_copy_is_only_approximate(sample, tmp_path):
    """The keyframe caveat, asserted rather than just claimed."""
    fast = cut_clip(sample, tmp_path / "f.mp4", 2.0, 5.0, accurate=False)
    exact = cut_clip(sample, tmp_path / "e.mp4", 2.0, 5.0, accurate=True)
    assert abs(duration(exact) - 3.0) < abs(duration(fast) - 3.0)


def test_concat_sums_durations(sample, tmp_path):
    a = cut_clip(sample, tmp_path / "a.mp4", 0, 2)
    b = cut_clip(sample, tmp_path / "b.mp4", 4, 6)
    joined = concat([a, b], tmp_path / "j.mp4")
    assert duration(joined) == pytest.approx(4.0, abs=0.2)


def test_concat_rejects_empty_input(tmp_path):
    with pytest.raises(ValueError):
        concat([], tmp_path / "j.mp4")


# ---------------------------------------------------------------- framing

def test_to_vertical_is_nine_by_sixteen(sample, tmp_path):
    out = to_vertical(sample, tmp_path / "v.mp4")
    video = next(s for s in probe(out)["streams"] if s["type"] == "video")
    assert (video["width"], video["height"]) == (1080, 1920)


def test_thumbnail_writes_an_image(sample, tmp_path):
    img = thumbnail(sample, tmp_path / "t.jpg")
    assert img.exists() and img.stat().st_size > 0


# ---------------------------------------------------------------- captions

@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00:00,000"),
    (1.5, "00:00:01,500"),
    (61.25, "00:01:01,250"),
    (3661.007, "01:01:01,007"),
])
def test_timestamp_formatting(seconds, expected):
    assert timestamp(seconds) == expected


def test_write_srt_round_trips(tmp_path):
    srt = write_srt([Cue(0, 1.5, "hello"), Cue(1.5, 3, "world")], tmp_path / "s.srt")
    text = srt.read_text()
    assert "00:00:00,000 --> 00:00:01,500" in text
    assert text.startswith("1\n")
    assert "\n2\n" in text


def test_split_long_cues_respects_max_chars():
    long_text = "word " * 30
    out = split_long_cues([Cue(0, 10, long_text)], max_chars=42)
    assert len(out) > 1
    assert all(len(c.text) <= 42 for c in out)
    assert out[0].start == 0
    assert out[-1].end == pytest.approx(10, abs=0.01)


def test_split_leaves_short_cues_alone():
    cue = Cue(0, 1, "short")
    assert split_long_cues([cue]) == [cue]


def test_burn_captions_produces_video(sample, tmp_path):
    srt = write_srt([Cue(0, 2, "burned in")], tmp_path / "s.srt")
    clip = cut_clip(sample, tmp_path / "c.mp4", 0, 3)
    out = burn_captions(clip, srt, tmp_path / "cap.mp4")
    assert duration(out) == pytest.approx(3.0, abs=0.2)


def test_filter_path_escaping():
    """Windows paths and timestamps in filenames both contain ':'."""
    assert _escape_filter_path("C:/a/b.srt") == r"'C\:/a/b.srt'"
    assert _escape_filter_path("a,b.srt") == r"'a\,b.srt'"


# ---------------------------------------------------------------- analysis

def test_detect_silence_finds_the_gap(sample):
    silences = detect_silence(sample, noise_db=-35, min_dur=0.5)
    assert len(silences) >= 1
    start, end = silences[0]
    assert start == pytest.approx(4.0, abs=0.3)
    assert end == pytest.approx(8.0, abs=0.3)


def test_speech_segments_invert_silence(sample):
    segments = speech_segments(sample, noise_db=-35, min_dur=0.5)
    assert len(segments) >= 2
    assert segments[0][0] == pytest.approx(0.0, abs=0.2)
    assert segments[-1][1] == pytest.approx(12.0, abs=0.3)


# ---------------------------------------------------------------- pipeline

def test_pick_highlight_prefers_dense_speech():
    cues = [Cue(0, 1, "hi"), Cue(20, 21, "a much longer line of speech here"),
            Cue(21, 22, "and another dense one right after it")]
    start, end = pick_highlight(cues, target=5.0)
    assert start == 20
    assert end == 25


def test_pick_highlight_handles_empty():
    assert pick_highlight([], target=30.0) == (0.0, 30.0)


def test_full_pipeline_produces_a_captioned_vertical_clip(sample, tmp_path):
    result = make_clip(sample, tmp_path / "out", target=6.0)
    final = tmp_path / "out" / "final.mp4"
    assert final.exists()
    video = next(s for s in probe(final)["streams"] if s["type"] == "video")
    assert (video["width"], video["height"]) == (1080, 1920)
    assert duration(final) == pytest.approx(6.0, abs=0.5)
    assert result["cues"] >= 1
