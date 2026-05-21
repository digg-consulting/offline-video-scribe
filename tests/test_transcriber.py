from pathlib import Path

from transcripto.hub_cache import repo_id_to_cache_folder
from transcripto.transcriber import (
    _MIN_WEIGHT_BYTES,
    is_model_cached,
    model_prereq_help,
    resolve_model_repo,
    whisper_snapshot_path,
)


def _layout_hub_cache(tmp_path, repo_id: str, files: dict[str, bytes]) -> Path:
    folder = tmp_path / repo_id_to_cache_folder(repo_id)
    snap = folder / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    for rel, data in files.items():
        path = snap / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return snap


def test_resolve_model_repo_aliases():
    assert resolve_model_repo("medium") == "mlx-community/whisper-medium-mlx"


def test_is_model_cached_true_when_weights_npz_in_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    _layout_hub_cache(
        tmp_path,
        "mlx-community/whisper-medium-mlx",
        {"config.json": b"{}", "weights.npz": b"x" * (_MIN_WEIGHT_BYTES + 1)},
    )
    assert is_model_cached("medium") is True


def test_is_model_cached_false_when_only_lfs_pointer(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    _layout_hub_cache(
        tmp_path,
        "mlx-community/whisper-medium-mlx",
        {
            "config.json": b"{}",
            "weights.npz": b"version https://git-lfs.github.com/spec/v1",
        },
    )
    assert is_model_cached("medium") is False


def test_is_model_cached_false_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "empty-hub"))
    assert is_model_cached("large-v3") is False


def test_whisper_snapshot_path_raises_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "empty-hub"))
    try:
        whisper_snapshot_path("medium")
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "hf download" in str(e)


def test_whisper_snapshot_path_returns_snapshot_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    snap = _layout_hub_cache(
        tmp_path,
        "mlx-community/whisper-medium-mlx",
        {"config.json": b"{}", "weights.npz": b"x" * (_MIN_WEIGHT_BYTES + 1)},
    )
    assert whisper_snapshot_path("medium") == snap


def test_model_prereq_help_mentions_hf_download():
    help_text = model_prereq_help("medium")
    assert "hf download" in help_text
    assert "transcripto check" in help_text
    assert "whisper-medium-mlx" in help_text


def test_no_try_to_load_from_cache_import():
    import transcripto.transcriber as tr

    source = open(tr.__file__, encoding="utf-8").read()
    assert "try_to_load_from_cache" not in source
