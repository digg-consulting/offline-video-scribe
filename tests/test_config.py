from importlib.resources import files
from pathlib import Path

import yaml

from ovs.config import (
    bundled_config_example_text,
    default_config_dict,
    load_config,
    write_default_config,
)
from ovs.xdg import config_example_path, default_config_path


def test_bundled_example_is_loadable():
    text = bundled_config_example_text()
    data = yaml.safe_load(text)
    assert data["model"] == "medium"
    assert data["formats"] == ["vtt", "txt"]
    assert data["diarization"] is True


def test_bundled_example_available_from_repo_or_package():
    pkg_path = files("ovs").joinpath("config.yaml.example")
    repo_path = Path(__file__).resolve().parents[1] / "config" / "config.yaml.example"
    assert pkg_path.is_file() or repo_path.is_file()


def test_default_config_dict_matches_example():
    d = default_config_dict()
    assert d["output_mode"] == "archive"
    assert d["formats"] == ["vtt", "txt"]
    assert d["diarization"] is True


def test_write_default_config_installs(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    dest = default_config_path()
    path, created = write_default_config(dest)
    assert created is True
    assert path == dest
    assert "formats:" in dest.read_text(encoding="utf-8")
    example = config_example_path()
    assert example.is_file()
    assert example.parent == dest.parent
    _, again = write_default_config(dest)
    assert again is False


def test_write_default_config_force(tmp_path: Path):
    dest = tmp_path / "config.yaml"
    write_default_config(dest)
    dest.write_text("model: small\n", encoding="utf-8")
    _, created = write_default_config(dest, force=True)
    assert created is True
    assert "medium" in dest.read_text(encoding="utf-8")


def test_load_config_from_yaml(tmp_path: Path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("model: medium\nlanguage: en\n", encoding="utf-8")
    monkeypatch.setenv("OVS_CONFIG", str(cfg_file))
    cfg = load_config()
    assert cfg.model == "medium"
    assert cfg.language == "en"
