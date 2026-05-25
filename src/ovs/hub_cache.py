"""Detect models in the Hugging Face hub cache (~/.cache/huggingface/hub)."""

from __future__ import annotations

from pathlib import Path

from ovs.xdg import hf_hub_cache_dir as _hf_hub_cache_dir


def hf_hub_cache_dir() -> Path:
    """Root of the HF hub cache (models--* directories)."""
    return _hf_hub_cache_dir()


def repo_id_to_cache_folder(repo_id: str) -> str:
    return "models--" + repo_id.replace("/", "--")


def hub_repo_dir(repo_id: str) -> Path | None:
    path = hf_hub_cache_dir() / repo_id_to_cache_folder(repo_id)
    return path if path.is_dir() else None


def iter_snapshot_dirs(repo_id: str):
    """Newest snapshot dirs first."""
    root = hub_repo_dir(repo_id)
    if root is None:
        return
    snaps = root / "snapshots"
    if not snaps.is_dir():
        return
    dirs = [p for p in snaps.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    yield from dirs


def find_cached_snapshot_path(repo_id: str, filename: str) -> Path | None:
    """Return a file path under snapshots/ without resolving blob symlinks."""
    for snap in iter_snapshot_dirs(repo_id):
        path = snap / filename
        if path.is_file():
            return path
    return None


def pipeline_snapshot_dir(repo_id: str, config_name: str = "config.yaml") -> Path | None:
    """Newest snapshot dir containing a pipeline config (for pyannote local load)."""
    cfg = find_cached_snapshot_path(repo_id, config_name)
    return cfg.parent if cfg is not None else None


def whisper_snapshot_dir(repo_id: str) -> Path | None:
    """Newest snapshot dir with Whisper config.json (for mlx-whisper offline load)."""
    return pipeline_snapshot_dir(repo_id, "config.json")


def find_cached_file(repo_id: str, filename: str) -> Path | None:
    """
    Resolve a repo file from the hub cache (newest snapshot first).
    """
    path = find_cached_snapshot_path(repo_id, filename)
    if path is None:
        return None
    try:
        return path.resolve()
    except OSError:
        return path


def find_cached_file_with_min_size(
    repo_id: str, filename: str, min_bytes: int
) -> Path | None:
    path = find_cached_file(repo_id, filename)
    if path is None:
        return None
    try:
        if path.stat().st_size >= min_bytes:
            return path
    except OSError:
        pass
    return None


def hub_repo_has_weight_files(repo_id: str, min_bytes: int = 100_000) -> bool:
    """True if any snapshot has a substantial weight-like file."""
    patterns = ("*.bin", "*.safetensors", "*.pt", "*.npz", "*.ckpt")
    for snap in iter_snapshot_dirs(repo_id):
        for pattern in patterns:
            for path in snap.rglob(pattern):
                if path.is_file():
                    try:
                        if path.stat().st_size >= min_bytes:
                            return True
                    except OSError:
                        continue
    return False


def whisper_cache_debug(model: str, repo_id: str) -> str:
    """Human-readable cache inspection for check --verbose."""
    lines = [f"  hub dir: {hf_hub_cache_dir() / repo_id_to_cache_folder(repo_id)}"]
    for name in ("config.json", "weights.npz", "weights.safetensors"):
        path = find_cached_file(repo_id, name)
        if path is None:
            lines.append(f"  {name}: not found in snapshots")
        else:
            try:
                size = path.stat().st_size
                lines.append(f"  {name}: {path} ({size:,} bytes)")
            except OSError as e:
                lines.append(f"  {name}: {path} (stat failed: {e})")
    return "\n".join(lines)


def diarization_cache_debug(pipeline_id: str) -> str:
    lines = [f"  hub dir: {hf_hub_cache_dir() / repo_id_to_cache_folder(pipeline_id)}"]
    cfg = find_cached_file(pipeline_id, "config.yaml")
    if cfg is None:
        lines.append("  config.yaml: not found in snapshots")
    else:
        lines.append(f"  config.yaml: {cfg}")
    lines.append(
        f"  weight files (>=100KB): {'yes' if hub_repo_has_weight_files(pipeline_id) else 'no'}"
    )
    return "\n".join(lines)
