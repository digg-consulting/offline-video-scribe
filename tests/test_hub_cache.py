from ovs.hub_cache import (
    find_cached_file,
    find_cached_file_with_min_size,
    hub_repo_has_weight_files,
    repo_id_to_cache_folder,
)
from ovs.transcriber import _MIN_WEIGHT_BYTES, is_model_cached


def _layout_hub_cache(tmp_path, repo_id: str, files: dict[str, bytes]) -> None:
    """files: relative path -> content under one snapshot."""
    folder = tmp_path / repo_id_to_cache_folder(repo_id)
    snap = folder / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    for rel, data in files.items():
        path = snap / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def test_find_cached_file_in_snapshots(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    _layout_hub_cache(
        tmp_path,
        "mlx-community/whisper-medium-mlx",
        {"config.json": b"{}", "weights.npz": b"x" * (_MIN_WEIGHT_BYTES + 1)},
    )
    assert find_cached_file("mlx-community/whisper-medium-mlx", "weights.npz") is not None
    assert find_cached_file_with_min_size(
        "mlx-community/whisper-medium-mlx",
        "weights.npz",
        _MIN_WEIGHT_BYTES,
    ) is not None


def test_is_model_cached_uses_snapshot_scan_only(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    _layout_hub_cache(
        tmp_path,
        "mlx-community/whisper-medium-mlx",
        {"config.json": b"{}", "weights.npz": b"x" * (_MIN_WEIGHT_BYTES + 1)},
    )
    assert is_model_cached("medium") is True


def test_hub_repo_has_weight_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    _layout_hub_cache(
        tmp_path,
        "pyannote/speaker-diarization-community-1",
        {
            "config.yaml": b"x: 1\n",
            "embedding/pytorch_model.bin": b"x" * 200_000,
        },
    )
    assert hub_repo_has_weight_files("pyannote/speaker-diarization-community-1") is True
