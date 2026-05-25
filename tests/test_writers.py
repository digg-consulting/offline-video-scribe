from pathlib import Path

from ovs.models import Segment
from ovs.writers import (
    format_full_text,
    format_srt,
    format_vtt,
    parse_vtt_cues,
    vtt_body_plain_copy,
    vtt_to_txt_diarized,
    write_formats,
)


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


def test_format_vtt_unchanged_with_speakers():
    segs = [
        Segment(0.0, 1.0, "One.", speaker="Speaker 1"),
        Segment(1.0, 2.0, "Two.", speaker="Speaker 1"),
    ]
    vtt = format_vtt(segs)
    assert vtt.count("-->") == 2
    assert "Speaker 1: One." in vtt
    assert "Speaker 1: Two." in vtt


def test_vtt_body_plain_copy():
    vtt = format_vtt(_segments())
    body = vtt_body_plain_copy(vtt)
    assert not body.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:02.500" in body
    assert "Hello world." in body


def test_parse_vtt_cues_extracts_speaker():
    vtt = format_vtt([Segment(0.0, 1.0, "Hi.", speaker="Speaker 1")])
    cues = parse_vtt_cues(vtt)
    assert len(cues) == 1
    assert cues[0].speaker == "Speaker 1"
    assert cues[0].text == "Hi."


def test_vtt_to_txt_diarized_bundles_same_speaker():
    vtt = format_vtt(
        [
            Segment(0.0, 10.0, "Transcript 1.", speaker="Speaker 1"),
            Segment(10.0, 20.0, "Transcript 2.", speaker="Speaker 1"),
            Segment(20.0, 30.0, "Transcript 3.", speaker="Speaker 1"),
        ]
    )
    txt = vtt_to_txt_diarized(vtt)
    assert txt.startswith("0:00 | Speaker 1\n")
    assert "Transcript 1." in txt
    assert "Transcript 2." in txt
    assert "Transcript 3." in txt
    assert txt.count("| Speaker") == 1


def test_vtt_to_txt_diarized_splits_speaker_change():
    vtt = format_vtt(
        [
            Segment(0.0, 10.0, "A.", speaker="Speaker 1"),
            Segment(90.0, 100.0, "B.", speaker="Speaker 2"),
        ]
    )
    txt = vtt_to_txt_diarized(vtt)
    assert "0:00 | Speaker 1" in txt
    assert "1:30 | Speaker 2" in txt
    assert txt.count("| Speaker") == 2


def test_vtt_to_txt_diarized_speaker_returns_later():
    vtt = format_vtt(
        [
            Segment(0.0, 1.0, "A.", speaker="Speaker 1"),
            Segment(1.0, 2.0, "B.", speaker="Speaker 2"),
            Segment(2.0, 3.0, "C.", speaker="Speaker 1"),
        ]
    )
    txt = vtt_to_txt_diarized(vtt)
    assert txt.count("| Speaker") == 3


def test_vtt_to_txt_diarized_human_short_timestamps():
    vtt = format_vtt([Segment(65.0, 70.0, "Late.", speaker="Speaker 1")])
    txt = vtt_to_txt_diarized(vtt)
    assert "1:05 | Speaker 1" in txt


def test_vtt_to_txt_diarized_hour_format():
    vtt = format_vtt([Segment(3600.0, 3605.0, "Hour.", speaker="Speaker 1")])
    txt = vtt_to_txt_diarized(vtt)
    assert "1:00:00 | Speaker 1" in txt


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
    vtt = (tmp_path / "a.vtt").read_text()
    txt = (tmp_path / "a.txt").read_text()
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:02.500" in txt
    assert "Hello world." in txt
    assert "Full text." not in txt
    assert "-->" in (tmp_path / "a.srt").read_text()


def test_write_formats_vtt_and_txt_diarized(tmp_path: Path):
    segs = [
        Segment(0.0, 1.0, "One.", speaker="Speaker 1"),
        Segment(1.0, 2.0, "Two.", speaker="Speaker 1"),
    ]
    out = {"txt": tmp_path / "a.txt", "vtt": tmp_path / "a.vtt"}
    write_formats("", segs, out, formats=["vtt", "txt"])
    vtt = (tmp_path / "a.vtt").read_text()
    txt = (tmp_path / "a.txt").read_text()
    assert vtt.count("-->") == 2
    assert "Speaker 1: One." in vtt
    assert "0:00 | Speaker 1" in txt
    assert "One." in txt
    assert "Two." in txt
    assert "Speaker 1: One." not in txt


def test_write_formats_txt_only_derives_from_vtt(tmp_path: Path):
    segs = [Segment(0.0, 2.0, "Only txt.", speaker="Speaker 1")]
    out = {"txt": tmp_path / "only.txt"}
    write_formats("", segs, out, formats=["txt"])
    txt = (tmp_path / "only.txt").read_text()
    assert "0:00 | Speaker 1" in txt
    assert "Only txt." in txt
    assert not (tmp_path / "only.vtt").exists()
