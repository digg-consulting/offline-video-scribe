"""XDG Base Directory paths for OVS (digg/ovs namespace)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def _home() -> Path:
    return Path.home()


def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", _home() / ".config")).expanduser()


def xdg_cache_home() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", _home() / ".cache")).expanduser()


def xdg_data_home() -> Path:
    return Path(
        os.environ.get("XDG_DATA_HOME", _home() / ".local" / "share")
    ).expanduser()


def ovs_config_dir() -> Path:
    """Config, preferences, and user settings: ~/.config/digg/ovs"""
    return xdg_config_home() / "digg" / "ovs"


def ovs_cache_dir() -> Path:
    """Cached files: ~/.cache/digg/ovs"""
    return xdg_cache_home() / "digg" / "ovs"


def ovs_data_dir() -> Path:
    """Tool install, libraries, assets: ~/.local/share/digg/ovs"""
    return xdg_data_home() / "digg" / "ovs"


def ovs_bin_dir() -> Path:
    """User executables: ~/.local/bin"""
    return _home() / ".local" / "bin"


def default_config_path() -> Path:
    """Active user settings (config + preferences)."""
    return ovs_config_dir() / "config.yaml"


def config_example_path() -> Path:
    """Bundled reference copy installed beside the active config."""
    return ovs_config_dir() / "config.yaml.example"


def legacy_config_path() -> Path:
    return _home() / ".config" / "ovs" / "config.yaml"


def ovs_hf_home_dir() -> Path:
    """Hugging Face home under the OVS cache (models + hub metadata)."""
    return ovs_cache_dir() / "huggingface"


def ovs_hf_hub_cache_dir() -> Path:
    return ovs_hf_home_dir() / "hub"


def legacy_hf_hub_cache_dir() -> Path:
    return _home() / ".cache" / "huggingface" / "hub"


def resolve_config_path(explicit: Path | None = None) -> Path:
    """Config file path: explicit arg, OVS_CONFIG, new XDG path, or legacy fallback."""
    if explicit is not None:
        return explicit.expanduser()
    env = os.environ.get("OVS_CONFIG")
    if env:
        return Path(env).expanduser()
    new = default_config_path()
    if new.is_file():
        return new
    legacy = legacy_config_path()
    if legacy.is_file():
        return legacy
    return new


def hf_hub_cache_dir() -> Path:
    """
    Hugging Face hub cache directory.

    Honors HF_HUB_CACHE and HF_HOME when set; otherwise prefers the OVS XDG cache,
    then a populated legacy ~/.cache/huggingface/hub tree.
    """
    if hub := os.environ.get("HF_HUB_CACHE"):
        return Path(hub).expanduser()
    if hf_home := os.environ.get("HF_HOME"):
        return Path(hf_home).expanduser() / "hub"
    new = ovs_hf_hub_cache_dir()
    legacy = legacy_hf_hub_cache_dir()
    if new.is_dir() and any(new.iterdir()):
        return new
    if legacy.is_dir() and any(legacy.iterdir()):
        return legacy
    return new


def hf_env_defaults() -> dict[str, str]:
    """Default HF_* paths under ~/.cache/digg/ovs (only when unset)."""
    hf_home = ovs_hf_home_dir()
    return {
        "HF_HOME": str(hf_home),
        "HF_HUB_CACHE": str(hf_home / "hub"),
    }


def apply_hf_env_defaults() -> None:
    for key, value in hf_env_defaults().items():
        os.environ.setdefault(key, value)


def ensure_xdg_dirs() -> None:
    """Create standard OVS directories (idempotent)."""
    for path in (
        ovs_config_dir(),
        ovs_cache_dir(),
        ovs_data_dir(),
        ovs_bin_dir(),
        ovs_hf_hub_cache_dir(),
        ovs_data_dir() / "tool",
    ):
        path.mkdir(parents=True, exist_ok=True)


def migrate_legacy_config_example() -> Path | None:
    """Move config.yaml.example from the old data dir into the config dir."""
    dest = config_example_path()
    if dest.is_file():
        return None
    legacy_share = ovs_data_dir() / "config.yaml.example"
    if not legacy_share.is_file():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(legacy_share), str(dest))
    return dest


def migrate_legacy_config(target: Path | None = None) -> Path | None:
    """
    Copy ~/.config/ovs/config.yaml to the XDG path when only the legacy file exists.

    Returns the new path when migrated, else None.
    """
    dest = (target or default_config_path()).expanduser()
    legacy = legacy_config_path()
    if dest.is_file() or not legacy.is_file():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy, dest)
    return dest
