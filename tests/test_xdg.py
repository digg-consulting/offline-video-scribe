from pathlib import Path

from ovs.xdg import (
    config_example_path,
    default_config_path,
    default_hf_hub_cache_dir,
    hf_env_defaults,
    hf_hub_cache_dir,
    legacy_config_path,
    legacy_digg_ovs_cache_dir,
    legacy_digg_ovs_config_dir,
    legacy_digg_ovs_data_dir,
    legacy_digg_ovs_hf_hub_cache_dir,
    legacy_hf_hub_cache_dir,
    migrate_legacy_config,
    migrate_legacy_config_example,
    migrate_legacy_digg_ovs_namespace,
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

    assert ovs_config_dir() == home / ".config" / "digg" / "offline-video-scribe"
    assert ovs_cache_dir() == home / ".cache" / "digg" / "offline-video-scribe"
    assert ovs_data_dir() == home / ".local" / "share" / "digg" / "offline-video-scribe"
    assert ovs_bin_dir() == home / ".local" / "bin"
    assert default_config_path() == ovs_config_dir() / "config.yaml"
    assert config_example_path() == ovs_config_dir() / "config.yaml.example"
    assert legacy_digg_ovs_hf_hub_cache_dir() == (
        home / ".cache" / "digg" / "ovs" / "huggingface" / "hub"
    )
    assert ovs_hf_hub_cache_dir() == legacy_digg_ovs_hf_hub_cache_dir()


def test_xdg_paths_respect_env_overrides(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    assert ovs_config_dir() == tmp_path / "cfg" / "digg" / "offline-video-scribe"
    assert ovs_cache_dir() == tmp_path / "cache" / "digg" / "offline-video-scribe"
    assert ovs_data_dir() == tmp_path / "data" / "digg" / "offline-video-scribe"


def test_hf_hub_cache_prefers_default_when_populated(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)

    default_hub = default_hf_hub_cache_dir()
    default_hub.mkdir(parents=True)
    (default_hub / "models--org--repo").mkdir()
    legacy_hub = legacy_digg_ovs_hf_hub_cache_dir()
    legacy_hub.mkdir(parents=True)
    (legacy_hub / "models--legacy--repo").mkdir()

    assert hf_hub_cache_dir() == default_hub


def test_hf_hub_cache_falls_back_to_legacy_ovs_when_only_legacy_populated(
    monkeypatch, tmp_path
):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)

    legacy_hub = legacy_digg_ovs_hf_hub_cache_dir()
    legacy_hub.mkdir(parents=True)
    (legacy_hub / "models--legacy--repo").mkdir()

    assert hf_hub_cache_dir() == legacy_hub


def test_hf_hub_cache_defaults_to_standard_path(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)

    assert hf_hub_cache_dir() == legacy_hf_hub_cache_dir()


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


def test_resolve_config_uses_legacy_digg_ovs_when_new_missing(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    legacy_digg = legacy_digg_ovs_config_dir() / "config.yaml"
    legacy_digg.parent.mkdir(parents=True)
    legacy_digg.write_text("model: small\n", encoding="utf-8")

    assert resolve_config_path() == legacy_digg


def test_migrate_legacy_digg_ovs_namespace(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    legacy_cfg = legacy_digg_ovs_config_dir() / "config.yaml"
    legacy_cfg.parent.mkdir(parents=True)
    legacy_cfg.write_text("model: small\n", encoding="utf-8")

    migrate_legacy_digg_ovs_namespace()
    assert default_config_path().read_text(encoding="utf-8") == "model: small\n"


def test_migrate_legacy_config_example_from_data_dir(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    legacy_example = legacy_digg_ovs_data_dir() / "config.yaml.example"
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


def test_hf_env_defaults_under_standard_cache(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)

    env = hf_env_defaults()
    assert env["HF_HOME"] == str(home / ".cache" / "huggingface")
    assert env["HF_HUB_CACHE"] == str(home / ".cache" / "huggingface" / "hub")
