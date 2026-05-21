from pathlib import Path

import mlx_whisper

from transcripto.models import Segment, TranscriptResult

MODEL_REPOS = {
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "medium-8bit": "mlx-community/whisper-medium-mlx-8bit",
    "small": "mlx-community/whisper-small-mlx",
}


def resolve_model_repo(model: str) -> str:
    if model in MODEL_REPOS:
        return MODEL_REPOS[model]
    if model.startswith("mlx-community/"):
        return model
    raise ValueError(
        f"unknown model: {model}. Choose from {list(MODEL_REPOS)} or mlx-community/..."
    )


_WEIGHT_FILES = ("weights.npz", "weights.safetensors", "model.safetensors")
# mlx-community Whisper repos ship multi-GB weights.npz; LFS pointers are ~100 bytes.
_MIN_WEIGHT_BYTES = 1_000_000


def _weight_in_snapshot(snap_dir: Path) -> Path | None:
    for filename in _WEIGHT_FILES:
        path = snap_dir / filename
        if not path.is_file():
            continue
        try:
            if path.stat().st_size >= _MIN_WEIGHT_BYTES:
                return path
        except OSError:
            continue
    return None


def is_model_cached(model: str) -> bool:
    """True if Whisper weights are present under a local hub snapshot (offline)."""
    from transcripto.hub_cache import whisper_snapshot_dir

    repo = resolve_model_repo(model)
    snap_dir = whisper_snapshot_dir(repo)
    if snap_dir is None:
        return False
    if not (snap_dir / "config.json").is_file():
        return False
    return _weight_in_snapshot(snap_dir) is not None


def whisper_snapshot_path(model: str) -> Path:
    """Local snapshot directory for mlx-whisper; raises if not ready for offline use."""
    from transcripto.hub_cache import whisper_snapshot_dir

    repo = resolve_model_repo(model)
    snap_dir = whisper_snapshot_dir(repo)
    if snap_dir is None or _weight_in_snapshot(snap_dir) is None:
        raise RuntimeError(model_prereq_help(model))
    return snap_dir


def model_prereq_help(model: str) -> str:
    """Instructions when the model is not in cache (user downloads outside transcripto)."""
    repo = resolve_model_repo(model)
    return f"""Whisper model '{model}' is not in your local Hugging Face cache.

Prepare with the Hugging Face CLI (see docs/HUGGINGFACE.md):

  hf auth login
  hf download {repo} --include "config.json" --include "weights.npz"
  transcripto check --model {model}
"""


def transcribe_audio(
    wav_path: Path | str,
    *,
    model: str = "medium",
    language: str | None = None,
    verbose: bool = False,
) -> TranscriptResult:
    snap_dir = whisper_snapshot_path(model)
    kwargs: dict = {"path_or_hf_repo": str(snap_dir), "verbose": verbose}
    if language and language != "auto":
        kwargs["language"] = language
    result = mlx_whisper.transcribe(str(wav_path), **kwargs)
    segments = [
        Segment(
            start=float(s["start"]),
            end=float(s["end"]),
            text=str(s["text"]).strip(),
        )
        for s in result.get("segments", [])
    ]
    return TranscriptResult(
        text=str(result.get("text", "")).strip(),
        segments=segments,
        language=result.get("language"),
    )
