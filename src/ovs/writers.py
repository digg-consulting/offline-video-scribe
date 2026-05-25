import json
import re
from dataclasses import dataclass
from pathlib import Path

from ovs.models import Segment

_SPEAKER_PREFIX = re.compile(r"^(Speaker \d+): (.*)$", re.DOTALL)
_VTT_TIMESTAMP = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3}) --> (\d{2}):(\d{2}):(\d{2})\.(\d{3})$"
)


@dataclass(frozen=True)
class VttCue:
    start: float
    end: float
    text: str
    speaker: str | None = None


def _ts_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ts_vtt(seconds: float) -> str:
    return _ts_srt(seconds).replace(",", ".")


def _ts_human_short(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _parse_vtt_timestamp(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _cue_text(seg: Segment) -> str:
    text = seg.text.strip()
    if seg.speaker:
        return f"{seg.speaker}: {text}"
    return text


def format_full_text(segments: list[Segment]) -> str:
    parts = [_cue_text(seg) for seg in segments if seg.text.strip()]
    return "\n\n".join(parts).strip() + ("\n" if parts else "")


def format_srt(segments: list[Segment]) -> str:
    blocks = []
    for i, seg in enumerate(segments, start=1):
        blocks.append(
            f"{i}\n{_ts_srt(seg.start)} --> {_ts_srt(seg.end)}\n{_cue_text(seg)}\n"
        )
    return "\n".join(blocks).strip() + "\n"


def format_vtt(segments: list[Segment]) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        if not seg.text.strip():
            continue
        lines.append(f"{_ts_vtt(seg.start)} --> {_ts_vtt(seg.end)}")
        lines.append(_cue_text(seg))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def vtt_body_plain_copy(vtt_content: str) -> str:
    """Return VTT cue body without the WEBVTT header."""
    lines = vtt_content.strip().splitlines()
    if lines and lines[0].strip() == "WEBVTT":
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    body = "\n".join(lines).strip()
    return body + "\n" if body else ""


def _split_cue_text(raw: str) -> tuple[str | None, str]:
    m = _SPEAKER_PREFIX.match(raw.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return None, raw.strip()


def parse_vtt_cues(vtt_content: str) -> list[VttCue]:
    """Parse cues from OVS-generated WebVTT."""
    lines = vtt_content.strip().splitlines()
    if lines and lines[0].strip() == "WEBVTT":
        lines = lines[1:]
    cues: list[VttCue] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        m = _VTT_TIMESTAMP.match(line)
        if not m:
            i += 1
            continue
        start = _parse_vtt_timestamp(m.group(1), m.group(2), m.group(3), m.group(4))
        end = _parse_vtt_timestamp(m.group(5), m.group(6), m.group(7), m.group(8))
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i])
            i += 1
        raw = "\n".join(text_lines).strip()
        speaker, text = _split_cue_text(raw)
        if text:
            cues.append(VttCue(start=start, end=end, text=text, speaker=speaker))
        i += 1
    return cues


def _group_contiguous_by_speaker(cues: list[VttCue]) -> list[list[VttCue]]:
    groups: list[list[VttCue]] = []
    current: list[VttCue] = []
    current_speaker: str | None | object = object()
    for cue in cues:
        if current_speaker is object() or cue.speaker != current_speaker:
            if current:
                groups.append(current)
            current = [cue]
            current_speaker = cue.speaker
        else:
            current.append(cue)
    if current:
        groups.append(current)
    return groups


def vtt_to_txt_diarized(vtt_content: str) -> str:
    """Bundled readable TXT from VTT cues (start-only human-short timestamps)."""
    cues = parse_vtt_cues(vtt_content)
    if not cues:
        return ""
    blocks: list[str] = []
    for group in _group_contiguous_by_speaker(cues):
        speaker = group[0].speaker or "Speaker 1"
        header = f"{_ts_human_short(group[0].start)} | {speaker}"
        texts = [c.text for c in group]
        blocks.append(header + "\n" + "\n\n".join(texts))
    return "\n\n".join(blocks).strip() + "\n"


def write_formats(
    full_text: str,
    segments: list[Segment],
    output_paths: dict[str, Path],
    *,
    formats: list[str],
) -> None:
    has_speakers = any(s.speaker for s in segments)
    json_text = (
        format_full_text(segments) if has_speakers else full_text.strip()
    )
    need_vtt = "txt" in formats or "vtt" in formats
    vtt_content = format_vtt(segments) if need_vtt else ""

    for fmt in formats:
        path = output_paths[fmt]
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "vtt":
            path.write_text(vtt_content, encoding="utf-8")
        elif fmt == "txt":
            if has_speakers:
                body = vtt_to_txt_diarized(vtt_content)
            else:
                body = vtt_body_plain_copy(vtt_content)
            path.write_text(body, encoding="utf-8")
        elif fmt == "srt":
            path.write_text(format_srt(segments), encoding="utf-8")
        elif fmt == "json":
            payload = {
                "text": json_text,
                "segments": [
                    {
                        "start": s.start,
                        "end": s.end,
                        "text": s.text,
                        **({"speaker": s.speaker} if s.speaker else {}),
                    }
                    for s in segments
                ],
            }
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        else:
            raise ValueError(f"unsupported format: {fmt}")
