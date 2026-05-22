"""Speaker diarization via pyannote (Speaker 1, Speaker 2, …)."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from ovs import CLI_NAME
from ovs.models import Segment, TranscriptResult

logger = logging.getLogger(__name__)

DIARIZATION_PIPELINE_ID = "pyannote/speaker-diarization-community-1"
HF_ACCEPT_URL = "https://huggingface.co/pyannote/speaker-diarization-community-1"


@dataclass(frozen=True)
class SpeakerTurn:
    start: float
    end: float
    label: str


def diarization_prereq_help() -> str:
    return f"""Diarization model is not in your local Hugging Face cache.

Prepare with the Hugging Face CLI (see docs/HUGGINGFACE.md):

  hf auth login
  # GATED — accept terms (browser, same HF account):
  {HF_ACCEPT_URL}

  hf download {DIARIZATION_PIPELINE_ID}
  {CLI_NAME} check
"""


def check_pyannote_available() -> None:
    try:
        import pyannote.audio  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "pyannote.audio is not installed. Run: uv sync"
        ) from e


def load_diarization_pipeline(pipeline_id: str = DIARIZATION_PIPELINE_ID):
    """Load the pyannote diarization pipeline from the local hub snapshot only."""
    check_pyannote_available()
    from pyannote.audio import Pipeline
    from ovs.hub_cache import pipeline_snapshot_dir

    snap_dir = pipeline_snapshot_dir(pipeline_id, "config.yaml")
    if snap_dir is None:
        raise RuntimeError(diarization_prereq_help())
    try:
        return Pipeline.from_pretrained(str(snap_dir))
    except Exception as e:
        raise RuntimeError(diarization_prereq_help()) from e


def run_diarization(
    audio_path: Path | str,
    pipeline,
    *,
    duration_s: float | None = None,
) -> list[SpeakerTurn]:
    """Return speaker turns for an audio file."""
    from ovs.ffmpeg_util import wav_duration_seconds

    path = Path(audio_path)
    if duration_s is None:
        duration_s = wav_duration_seconds(path)
    t0 = time.monotonic()

    done = threading.Event()

    def _heartbeat() -> None:
        while not done.wait(60.0):
            elapsed = int(time.monotonic() - t0)
            logger.info(
                "diarization in progress (%ds elapsed; long recordings can take 10–30+ min)…",
                elapsed,
            )

    heartbeat = threading.Thread(target=_heartbeat, daemon=True)
    heartbeat.start()
    try:
        output = pipeline(str(audio_path))
    finally:
        done.set()
        heartbeat.join(timeout=1.0)

    elapsed = time.monotonic() - t0
    turns: list[SpeakerTurn] = []
    for turn, speaker in output.speaker_diarization:
        turns.append(
            SpeakerTurn(
                start=float(turn.start),
                end=float(turn.end),
                label=str(speaker),
            )
        )
    logger.info(
        "diarization finished in %.0fs (%d speaker turns)",
        elapsed,
        len(turns),
    )
    return turns


def _speaker_for_segment(
    start: float, end: float, turns: list[SpeakerTurn]
) -> str | None:
    """Pick the speaker label with the largest time overlap."""
    best_label: str | None = None
    best_overlap = 0.0
    for turn in turns:
        overlap = max(0.0, min(end, turn.end) - max(start, turn.start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_label = turn.label
    if best_label is not None:
        return best_label
    mid = (start + end) / 2
    for turn in turns:
        if turn.start <= mid <= turn.end:
            return turn.label
    return None


def _display_speaker(raw: str | None, label_map: dict[str, str]) -> str:
    if raw is None:
        return "Speaker 1"
    if raw not in label_map:
        label_map[raw] = f"Speaker {len(label_map) + 1}"
    return label_map[raw]


def apply_diarization(
    result: TranscriptResult,
    turns: list[SpeakerTurn],
) -> TranscriptResult:
    """Attach Speaker 1 / Speaker 2 labels to transcript segments."""
    label_map: dict[str, str] = {}
    segments: list[Segment] = []
    for seg in result.segments:
        raw = _speaker_for_segment(seg.start, seg.end, turns)
        speaker = _display_speaker(raw, label_map)
        segments.append(
            Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text,
                speaker=speaker,
            )
        )
    from ovs.writers import format_full_text

    return TranscriptResult(
        text=format_full_text(segments),
        segments=segments,
        language=result.language,
    )
