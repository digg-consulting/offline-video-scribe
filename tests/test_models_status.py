from unittest.mock import MagicMock, patch

from ovs.config import AppConfig
from ovs.models_status import (
    all_models_cached,
    is_diarization_cached,
    models_prereq_help,
)


@patch(
    "ovs.models_status.diarization_cache_status",
    return_value=(True, "ok"),
)
@patch("ovs.models_status.is_model_cached", return_value=True)
def test_all_models_cached(_mock_whisper, _mock_dia):
    cfg = AppConfig(diarization=True)
    assert all_models_cached(cfg) is True


@patch("ovs.models_status.pipeline_snapshot_dir")
@patch("ovs.models_status.hub_repo_has_weight_files", return_value=True)
@patch("pyannote.audio.Pipeline")
@patch("ovs.models_status.check_pyannote_available")
def test_is_diarization_cached_offline(
    mock_check, mock_pipeline_cls, _weights, mock_snap
):
    mock_snap.return_value = __import__("pathlib").Path("/fake/snapshot")
    mock_check.return_value = None
    mock_pipeline_cls.from_pretrained.return_value = MagicMock()
    assert is_diarization_cached() is True
    mock_pipeline_cls.from_pretrained.assert_called_once_with("/fake/snapshot")


def test_models_prereq_help_mentions_hf_download():
    cfg = AppConfig(model="medium", diarization=True)
    text = models_prereq_help(cfg)
    assert "hf download" in text
    assert "mlx-community/whisper-medium-mlx" in text
    assert "offline-video-scribe check" in text
    assert "models download" not in text
