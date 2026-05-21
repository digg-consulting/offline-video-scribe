from pathlib import Path

from ovs.models import Segment
from ovs.writers import format_full_text, format_srt, format_vtt, write_formats


def _segments():
    return [
        Segment(0.0, 2.5, "Hello world."),
        Segment(2.5, 5.0, "Second line."),
    ]


def test_format_srt():
    srt = format_srt(_segments())
    assert "00:00:00,000 --> 00:00:02,500" in srt
    assert "Hello world." in srt
    assert srt.strip().endswith("Second line.")


def test_format_srt_with_speaker():
    segs = [Segment(0.0, 2.0, "Hello.", speaker="Speaker 1")]
    srt = format_srt(segs)
    assert "Speaker 1: Hello." in srt


def test_format_vtt():
    vtt = format_vtt(_segments())
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:02.500" in vtt


def test_format_full_text_with_speakers():
    segs = [
        Segment(0.0, 1.0, "Hi.", speaker="Speaker 1"),
        Segment(1.0, 2.0, "Hey.", speaker="Speaker 2"),
    ]
    text = format_full_text(segs)
    assert "Speaker 1: Hi." in text
    assert "Speaker 2: Hey." in text


def test_write_formats_creates_files(tmp_path: Path):
    out = {
        "txt": tmp_path / "a.txt",
        "srt": tmp_path / "a.srt",
        "vtt": tmp_path / "a.vtt",
    }
    write_formats("Full text.", _segments(), out, formats=["txt", "srt", "vtt"])
    assert (tmp_path / "a.txt").read_text() == "Full text.\n"
    assert "-->" in (tmp_path / "a.srt").read_text()
    assert (tmp_path / "a.vtt").read_text().startswith("WEBVTT")
