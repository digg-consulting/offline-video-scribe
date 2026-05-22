import os
from unittest.mock import patch

from ovs.cli import main
from ovs.offline import apply_runtime_offline_env, is_runtime_command


def test_is_runtime_command():
    assert is_runtime_command("transcribe") is True
    assert is_runtime_command("check") is True
    assert is_runtime_command(None) is False


def test_apply_runtime_offline_env(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)
    apply_runtime_offline_env()
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.environ.get("HF_HUB_DISABLE_TELEMETRY") == "1"
    assert os.environ.get("HF_HOME") == str(home / ".cache" / "digg" / "ovs" / "huggingface")
    assert os.environ.get("HF_HUB_CACHE") == str(
        home / ".cache" / "digg" / "ovs" / "huggingface" / "hub"
    )


@patch("ovs.cli.cmd_check", return_value=0)
@patch("ovs.cli.build_parser")
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
