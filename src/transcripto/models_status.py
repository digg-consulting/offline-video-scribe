"""Verify locally cached models (offline only — no Hugging Face downloads)."""

from __future__ import annotations

from transcripto.config import AppConfig
from transcripto.diarization import (
    DIARIZATION_PIPELINE_ID,
    check_pyannote_available,
)
from transcripto.hub_cache import (
    diarization_cache_debug,
    hub_repo_has_weight_files,
    pipeline_snapshot_dir,
    whisper_cache_debug,
)
from transcripto.transcriber import is_model_cached, resolve_model_repo


def diarization_cache_status(
    pipeline_id: str = DIARIZATION_PIPELINE_ID,
) -> tuple[bool, str]:
    """
    Return (ok, detail). Checks hub layout first, then pyannote local load.
    """
    snap_dir = pipeline_snapshot_dir(pipeline_id, "config.yaml")
    cfg_path = snap_dir / "config.yaml" if snap_dir else None
    has_weights = hub_repo_has_weight_files(pipeline_id)
    if cfg_path is None:
        return False, "config.yaml not in hub cache snapshots"
    if not has_weights:
        return (
            False,
            "hub folder exists but weight files look missing or incomplete "
            f"(try: hf download {pipeline_id})",
        )
    try:
        check_pyannote_available()
        from pyannote.audio import Pipeline

        Pipeline.from_pretrained(str(snap_dir))
        return True, "loaded from local cache"
    except Exception as e:
        return False, f"cache present but pyannote load failed: {type(e).__name__}: {e}"


def is_diarization_cached(pipeline_id: str = DIARIZATION_PIPELINE_ID) -> bool:
    """True if the diarization pipeline can load from local cache only."""
    ok, _ = diarization_cache_status(pipeline_id)
    return ok


def models_prereq_help(cfg: AppConfig) -> str:
    """Instructions when offline prerequisites are not met."""
    repo = resolve_model_repo(cfg.model)
    lines = [
        "Offline prerequisites not met — models must be downloaded before using transcripto.",
        "",
        "Prepare with the Hugging Face CLI (not transcripto):",
        "",
        "  brew install huggingface-cli",
        "  hf auth login",
        "  hf whoami",
    ]
    if cfg.diarization:
        lines.extend(
            [
                "",
                "  # Gated — accept terms (browser, same HF account):",
                "  # https://huggingface.co/pyannote/speaker-diarization-community-1",
            ]
        )
    lines.extend(
        [
            "",
            f'  hf download {repo} --include "config.json" --include "weights.npz"',
        ]
    )
    if cfg.diarization:
        lines.append(f"  hf download {cfg.diarization_pipeline}")
    lines.extend(
        [
            "",
            "  transcripto check",
            "",
            "See docs/HUGGINGFACE.md",
        ]
    )
    return "\n".join(lines)


def models_status(cfg: AppConfig) -> list[tuple[str, bool, str]]:
    """Return (name, ok, detail) for each required model."""
    items: list[tuple[str, bool, str]] = []
    repo = resolve_model_repo(cfg.model)
    whisper_ok = is_model_cached(cfg.model)
    whisper_detail = repo if whisper_ok else f"{repo} (not ready)"
    items.append((f"whisper/{cfg.model}", whisper_ok, whisper_detail))
    if cfg.diarization:
        dia_ok, dia_detail = diarization_cache_status(cfg.diarization_pipeline)
        items.append(
            (
                "diarization",
                dia_ok,
                cfg.diarization_pipeline if dia_ok else dia_detail,
            )
        )
    return items


def models_status_verbose(cfg: AppConfig) -> str:
    """Extra filesystem / load diagnostics for check --verbose."""
    lines: list[str] = []
    repo = resolve_model_repo(cfg.model)
    lines.append("whisper cache:")
    lines.append(whisper_cache_debug(cfg.model, repo))
    if cfg.diarization:
        lines.append("diarization cache:")
        lines.append(diarization_cache_debug(cfg.diarization_pipeline))
        _, detail = diarization_cache_status(cfg.diarization_pipeline)
        lines.append(f"  status: {detail}")
    return "\n".join(lines)


def all_models_cached(cfg: AppConfig) -> bool:
    return all(ok for _, ok, _ in models_status(cfg))
