"""XDG Base Directory paths for Offline Video Scribe (digg/offline-video-scribe)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# On-disk namespace (CLI alias remains `ovs` in ~/.local/bin only).
_APP_SLUG = "offline-video-scribe"
_LEGACY_APP_SLUG = "ovs"


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


def _digg_dir(base: Path, slug: str) -> Path:
    return base / "digg" / slug


def ovs_config_dir() -> Path:
    """Config and preferences: ~/.config/digg/offline-video-scribe"""
    return _digg_dir(xdg_config_home(), _APP_SLUG)


def ovs_cache_dir() -> Path:
    """App-specific cache (legacy HF fallback): ~/.cache/digg/offline-video-scribe"""
    return _digg_dir(xdg_cache_home(), _APP_SLUG)


def ovs_data_dir() -> Path:
    """Tool install root (uv tool): ~/.local/share/digg/offline-video-scribe"""
    return _digg_dir(xdg_data_home(), _APP_SLUG)


def legacy_digg_ovs_config_dir() -> Path:
    """Pre-rename config dir: ~/.config/digg/ovs"""
    return _digg_dir(xdg_config_home(), _LEGACY_APP_SLUG)


def legacy_digg_ovs_data_dir() -> Path:
    """Pre-rename data dir: ~/.local/share/digg/ovs"""
    return _digg_dir(xdg_data_home(), _LEGACY_APP_SLUG)


def legacy_digg_ovs_cache_dir() -> Path:
    """Pre-rename cache dir: ~/.cache/digg/ovs"""
    return _digg_dir(xdg_cache_home(), _LEGACY_APP_SLUG)


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


def default_hf_home_dir() -> Path:
    """Standard Hugging Face home (same as the HF CLI default)."""
    return xdg_cache_home() / "huggingface"


def default_hf_hub_cache_dir() -> Path:
    """Standard Hugging Face hub cache: ~/.cache/huggingface/hub"""
    return default_hf_home_dir() / "hub"


def legacy_digg_ovs_hf_hub_cache_dir() -> Path:
    """Pre-rename HF hub cache: ~/.cache/digg/ovs/huggingface/hub"""
    return legacy_digg_ovs_cache_dir() / "huggingface" / "hub"


def ovs_hf_hub_cache_dir() -> Path:
    """Alias kept for tests; same as legacy_digg_ovs HF hub path."""
    return legacy_digg_ovs_hf_hub_cache_dir()


def legacy_hf_hub_cache_dir() -> Path:
    """Alias for the standard hub cache path (kept for tests and docs)."""
    return default_hf_hub_cache_dir()


def resolve_config_path(explicit: Path | None = None) -> Path:
    """Config file path: explicit arg, OVS_CONFIG, new XDG path, or legacy fallbacks."""
    if explicit is not None:
        return explicit.expanduser()
    env = os.environ.get("OVS_CONFIG")
    if env:
        return Path(env).expanduser()
    new = default_config_path()
    if new.is_file():
        return new
    legacy_digg = legacy_digg_ovs_config_dir() / "config.yaml"
    if legacy_digg.is_file():
        return legacy_digg
    legacy = legacy_config_path()
    if legacy.is_file():
        return legacy
    return new


def _hub_cache_populated(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def hf_hub_cache_dir() -> Path:
    """
    Hugging Face hub cache directory.

    Honors HF_HUB_CACHE and HF_HOME when set; otherwise prefers
    ~/.cache/huggingface/hub, then a populated ~/.cache/digg/ovs/huggingface/hub tree.
    """
    if hub := os.environ.get("HF_HUB_CACHE"):
        return Path(hub).expanduser()
    if hf_home := os.environ.get("HF_HOME"):
        return Path(hf_home).expanduser() / "hub"
    default = default_hf_hub_cache_dir()
    legacy_ovs = legacy_digg_ovs_hf_hub_cache_dir()
    if _hub_cache_populated(default):
        return default
    if _hub_cache_populated(legacy_ovs):
        return legacy_ovs
    return default


def hf_env_defaults() -> dict[str, str]:
    """Default HF_* paths under ~/.cache/huggingface (only when unset)."""
    hf_home = default_hf_home_dir()
    return {
        "HF_HOME": str(hf_home),
        "HF_HUB_CACHE": str(hf_home / "hub"),
    }


def apply_hf_env_defaults() -> None:
    for key, value in hf_env_defaults().items():
        os.environ.setdefault(key, value)


def migrate_legacy_digg_ovs_namespace() -> None:
    """Copy config from ~/.config/digg/ovs into ~/.config/digg/offline-video-scribe."""
    dest_dir = ovs_config_dir()
    legacy_dir = legacy_digg_ovs_config_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_cfg = default_config_path()
    legacy_cfg = legacy_dir / "config.yaml"
    if not dest_cfg.is_file() and legacy_cfg.is_file():
        shutil.copy2(legacy_cfg, dest_cfg)
    dest_ex = config_example_path()
    legacy_ex = legacy_dir / "config.yaml.example"
    if not dest_ex.is_file() and legacy_ex.is_file():
        shutil.copy2(legacy_ex, dest_ex)


def ensure_xdg_dirs() -> None:
    """Create standard directories (idempotent)."""
    migrate_legacy_digg_ovs_namespace()
    for path in (
        ovs_config_dir(),
        ovs_cache_dir(),
        ovs_data_dir(),
        ovs_bin_dir(),
        default_hf_hub_cache_dir(),
    ):
        path.mkdir(parents=True, exist_ok=True)


def migrate_legacy_config_example() -> Path | None:
    """Move config.yaml.example from legacy data dirs into the config dir."""
    dest = config_example_path()
    if dest.is_file():
        return None
    for legacy_share in (
        ovs_data_dir() / "config.yaml.example",
        legacy_digg_ovs_data_dir() / "config.yaml.example",
        legacy_digg_ovs_data_dir() / "tool" / "config.yaml.example",
    ):
        if legacy_share.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy_share), str(dest))
            return dest
    return None


def migrate_legacy_config(target: Path | None = None) -> Path | None:
    """
    Copy legacy config files to the current XDG path when only an older file exists.

    Returns the new path when migrated, else None.
    """
    dest = (target or default_config_path()).expanduser()
    if dest.is_file():
        return None
    for legacy in (
        legacy_digg_ovs_config_dir() / "config.yaml",
        legacy_config_path(),
    ):
        if legacy.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy, dest)
            return dest
    return None
