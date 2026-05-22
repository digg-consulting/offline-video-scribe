from pathlib import Path

from ovs.xdg import (
    config_example_path,
    default_config_path,
    hf_env_defaults,
    hf_hub_cache_dir,
    legacy_config_path,
    legacy_hf_hub_cache_dir,
    migrate_legacy_config,
    migrate_legacy_config_example,
    ovs_bin_dir,
    ovs_cache_dir,
    ovs_config_dir,
    ovs_data_dir,
    ovs_hf_hub_cache_dir,
    resolve_config_path,
)


def test_xdg_paths_default_layout(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    assert ovs_config_dir() == home / ".config" / "digg" / "ovs"
    assert ovs_cache_dir() == home / ".cache" / "digg" / "ovs"
    assert ovs_data_dir() == home / ".local" / "share" / "digg" / "ovs"
    assert ovs_bin_dir() == home / ".local" / "bin"
    assert default_config_path() == ovs_config_dir() / "config.yaml"
    assert config_example_path() == ovs_config_dir() / "config.yaml.example"
    assert ovs_hf_hub_cache_dir() == ovs_cache_dir() / "huggingface" / "hub"


def test_xdg_paths_respect_env_overrides(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    assert ovs_config_dir() == tmp_path / "cfg" / "digg" / "ovs"
    assert ovs_cache_dir() == tmp_path / "cache" / "digg" / "ovs"
    assert ovs_data_dir() == tmp_path / "data" / "digg" / "ovs"


def test_hf_hub_cache_prefers_xdg_when_populated(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)

    new_hub = ovs_hf_hub_cache_dir()
    new_hub.mkdir(parents=True)
    (new_hub / "models--org--repo").mkdir()
    legacy = legacy_hf_hub_cache_dir()
    legacy.mkdir(parents=True)
    (legacy / "models--legacy--repo").mkdir()

    assert hf_hub_cache_dir() == new_hub


def test_hf_hub_cache_falls_back_to_legacy(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)

    legacy = legacy_hf_hub_cache_dir()
    legacy.mkdir(parents=True)
    (legacy / "models--legacy--repo").mkdir()

    assert hf_hub_cache_dir() == legacy


def test_resolve_config_prefers_new_over_legacy(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    legacy = legacy_config_path()
    legacy.parent.mkdir(parents=True)
    legacy.write_text("model: small\n", encoding="utf-8")
    new = default_config_path()
    new.parent.mkdir(parents=True)
    new.write_text("model: medium\n", encoding="utf-8")

    assert resolve_config_path() == new


def test_migrate_legacy_config_example_from_data_dir(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    legacy_example = ovs_data_dir() / "config.yaml.example"
    legacy_example.parent.mkdir(parents=True)
    legacy_example.write_text("model: small\n", encoding="utf-8")
    dest = config_example_path()

    migrated = migrate_legacy_config_example()
    assert migrated == dest
    assert dest.read_text(encoding="utf-8") == "model: small\n"
    assert not legacy_example.exists()


def test_migrate_legacy_config(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    legacy = legacy_config_path()
    legacy.parent.mkdir(parents=True)
    legacy.write_text("model: small\n", encoding="utf-8")
    dest = default_config_path()

    migrated = migrate_legacy_config(dest)
    assert migrated == dest
    assert dest.read_text(encoding="utf-8") == "model: small\n"


def test_hf_env_defaults_under_ovs_cache(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)

    env = hf_env_defaults()
    assert env["HF_HOME"] == str(ovs_cache_dir() / "huggingface")
    assert env["HF_HUB_CACHE"] == str(ovs_hf_hub_cache_dir())
