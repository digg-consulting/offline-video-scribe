from ovs.diarization import SpeakerTurn, apply_diarization
from ovs.models import Segment, TranscriptResult


def test_apply_diarization_labels_speakers():
    result = TranscriptResult(
        text="Hello. Hi.",
        segments=[
            Segment(0.0, 2.0, "Hello."),
            Segment(2.0, 4.0, "Hi."),
        ],
    )
    turns = [
        SpeakerTurn(0.0, 2.0, "SPEAKER_00"),
        SpeakerTurn(2.0, 4.0, "SPEAKER_01"),
    ]
    out = apply_diarization(result, turns)
    assert out.segments[0].speaker == "Speaker 1"
    assert out.segments[1].speaker == "Speaker 2"
    assert "Speaker 1: Hello." in out.text


def test_apply_diarization_single_speaker_default():
    result = TranscriptResult(
        text="Only me.",
        segments=[Segment(0.0, 3.0, "Only me.")],
    )
    out = apply_diarization(result, [])
    assert out.segments[0].speaker == "Speaker 1"
