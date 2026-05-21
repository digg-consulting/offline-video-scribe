import logging
from pathlib import Path
from typing import Any

from transcripto.config import AppConfig
from transcripto.diarization import apply_diarization, load_diarization_pipeline, run_diarization
from transcripto.ffmpeg_util import extract_audio_wav, wav_duration_seconds
from transcripto.paths import (
    OutputMode,
    move_video_to_archive,
    output_paths_for,
    should_skip,
)
from transcripto.transcriber import transcribe_audio
from transcripto.writers import write_formats

logger = logging.getLogger(__name__)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def discover_videos(
    path: Path,
    *,
    extensions: list[str],
    recursive: bool,
    exclude_under: Path | None = None,
) -> list[Path]:
    ext_set = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions}
    if path.is_file():
        if path.suffix.lower() not in ext_set:
            return []
        if exclude_under and _is_under(path, exclude_under):
            return []
        return [path]
    pattern = "**/*" if recursive else "*"
    root_exclude = exclude_under.resolve() if exclude_under else None
    return sorted(
        p
        for p in path.glob(pattern)
        if p.is_file()
        and p.suffix.lower() in ext_set
        and (root_exclude is None or not _is_under(p, root_exclude))
    )


def run_job(
    video: Path,
    cfg: AppConfig,
    *,
    force: bool = False,
    verbose: bool = False,
    mirror_root: Path | None = None,
    diarization_pipeline: Any | None = None,
) -> str:
    """Returns: 'ok' | 'skipped' | 'failed'"""
    out_paths = output_paths_for(
        video,
        output_mode=cfg.output_mode,
        output_dir=cfg.output_dir,
        formats=cfg.formats,
        mirror_root=mirror_root,
    )
    if should_skip(
        out_paths,
        formats=cfg.formats,
        force=force,
        video_path=video,
        output_mode=cfg.output_mode,
    ):
        logger.info("skip %s (outputs exist)", video)
        return "skipped"

    wav: Path | None = None
    try:
        logger.info("extract audio: %s", video)
        wav = extract_audio_wav(video)
        logger.info("transcribe: %s", video)
        lang = None if cfg.language == "auto" else cfg.language
        result = transcribe_audio(
            wav,
            model=cfg.model,
            language=lang,
            verbose=verbose,
        )
        if cfg.diarization:
            duration_s = wav_duration_seconds(wav) if wav else None
            if duration_s is not None:
                logger.info(
                    "diarize: %s (%.0f min audio — may take 10–30+ min, progress logged every 60s)",
                    video,
                    duration_s / 60,
                )
            else:
                logger.info("diarize: %s", video)
            pipeline = diarization_pipeline or load_diarization_pipeline(
                cfg.diarization_pipeline
            )
            turns = run_diarization(wav, pipeline, duration_s=duration_s)
            result = apply_diarization(result, turns)
        write_formats(result.text, result.segments, out_paths, formats=cfg.formats)
        if cfg.output_mode == OutputMode.ARCHIVE:
            dest = move_video_to_archive(video, out_paths)
            logger.info("archived video: %s", dest)
        logger.info(
            "wrote %s",
            ", ".join(str(out_paths[f]) for f in cfg.formats),
        )
        return "ok"
    except Exception:
        logger.exception("failed: %s", video)
        return "failed"
    finally:
        if wav is not None:
            wav.unlink(missing_ok=True)


def run_batch(
    paths: list[Path],
    cfg: AppConfig,
    *,
    force: bool = False,
    verbose: bool = False,
    input_root: Path | None = None,
) -> int:
    """Exit code: 0 all ok/skipped, 1 any failed, 2 no inputs."""
    if not paths:
        return 2
    counts = {"ok": 0, "skipped": 0, "failed": 0}
    mirror_root = None
    if cfg.output_mode == OutputMode.MIRROR and input_root is not None:
        mirror_root = input_root.resolve()
    exclude_under = (
        cfg.output_dir.resolve()
        if cfg.output_mode == OutputMode.ARCHIVE
        else None
    )
    diarization_pipeline = None
    if cfg.diarization:
        logger.info("loading diarization pipeline: %s", cfg.diarization_pipeline)
        diarization_pipeline = load_diarization_pipeline(cfg.diarization_pipeline)
    for video in paths:
        status = run_job(
            video,
            cfg,
            force=force,
            verbose=verbose,
            mirror_root=mirror_root,
            diarization_pipeline=diarization_pipeline,
        )
        counts[status] += 1
    if counts["failed"]:
        return 1
    return 0
