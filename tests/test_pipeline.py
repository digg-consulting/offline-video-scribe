from pathlib import Path
from unittest.mock import patch

from ovs.config import AppConfig
from ovs.paths import OutputMode
from ovs.pipeline import discover_videos, run_job


def test_discover_excludes_archive_output_dir(tmp_path: Path):
    out_root = tmp_path / "Transcripts"
    archived = out_root / "done" / "done.mov"
    archived.parent.mkdir(parents=True)
    archived.write_bytes(b"v")
    incoming = tmp_path / "incoming" / "new.mov"
    incoming.parent.mkdir(parents=True)
    incoming.write_bytes(b"v")
    found = discover_videos(
        tmp_path,
        extensions=[".mov"],
        recursive=True,
        exclude_under=out_root,
    )
    assert incoming in found
    assert archived not in found


@patch("ovs.pipeline.run_diarization")
@patch("ovs.pipeline.load_diarization_pipeline")
@patch("ovs.pipeline.transcribe_audio")
@patch("ovs.pipeline.extract_audio_wav")
def test_run_job_archive_moves_video(
    mock_extract, mock_transcribe, mock_load_pipe, mock_diarize, tmp_path: Path
):
    from ovs.models import Segment, TranscriptResult

    video = tmp_path / "incoming" / "clip.mov"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"fake-video")
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"wav")
    mock_extract.return_value = wav
    mock_transcribe.return_value = TranscriptResult(
        text="hello",
        segments=[Segment(start=0.0, end=1.0, text="hello")],
        language="en",
    )
    out_root = tmp_path / "Transcripts"
    cfg = AppConfig(
        output_mode=OutputMode.ARCHIVE,
        output_dir=out_root,
        formats=["vtt"],
        diarization=False,
    )
    assert run_job(video, cfg) == "ok"
    assert not video.exists()
    assert (out_root / "clip" / "clip.mov").is_file()
    assert (out_root / "clip" / "clip.vtt").is_file()
