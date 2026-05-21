import os
from unittest.mock import patch

from transcripto.cli import main
from transcripto.offline import apply_runtime_offline_env, is_runtime_command


def test_is_runtime_command():
    assert is_runtime_command("transcribe") is True
    assert is_runtime_command("check") is True
    assert is_runtime_command(None) is False


def test_apply_runtime_offline_env():
    apply_runtime_offline_env()
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.environ.get("HF_HUB_DISABLE_TELEMETRY") == "1"


@patch("transcripto.cli.cmd_check", return_value=0)
@patch("transcripto.cli.build_parser")
def test_main_sets_offline_env_for_check(mock_build, _mock_check):
    mock_build.return_value.parse_args.return_value = type(
        "Args",
        (),
        {"command": "check", "func": _mock_check},
    )()
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("HF_HUB_OFFLINE", None)
        try:
            main()
        except SystemExit:
            pass
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
