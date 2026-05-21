from unittest.mock import patch

from ovs.cli import cmd_transcribe
from ovs.config import AppConfig


@patch("ovs.cli.discover_videos", return_value=[])
@patch("ovs.cli.all_models_cached", return_value=True)
def test_transcribe_exits_when_no_videos(_cached, _discover, tmp_path):
    video = tmp_path / "test.mov"
    video.touch()
    args = type(
        "Args",
        (),
        {
            "verbose": False,
            "config": None,
            "path": [str(video)],
            "model": None,
            "language": None,
            "output_mode": None,
            "output_dir": None,
            "formats": None,
            "no_diarization": False,
            "force": False,
            "recursive": True,
        },
    )()
    with patch("ovs.cli.load_config", return_value=AppConfig()):
        code = cmd_transcribe(args)
    assert code == 2  # run_batch: no inputs
