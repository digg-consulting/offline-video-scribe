import argparse
import logging
import sys
from pathlib import Path

from transcripto import __version__
from transcripto.config import load_config, write_default_config
from transcripto.ffmpeg_util import FfmpegNotFoundError, require_ffmpeg
from transcripto.models_status import (
    all_models_cached,
    models_prereq_help,
    models_status,
    models_status_verbose,
)
from transcripto.offline import apply_runtime_offline_env, is_runtime_command
from transcripto.paths import OutputMode
from transcripto.pipeline import discover_videos, run_batch
from transcripto.diarization import check_pyannote_available
from transcripto.watcher import run_watch


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def cmd_init(args: argparse.Namespace) -> int:
    dest = Path(args.config).expanduser() if args.config else None
    path, created = write_default_config(dest, force=args.force)
    if created:
        label = "Replaced" if args.force else "Installed"
        print(f"{label} config: {path}")
    else:
        print(f"Config already exists: {path}")
        print("Use --force to replace with the bundled default.")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    """Write config and verify offline prerequisites."""
    print("=== transcripto setup ===\n")
    cfg_path, created = write_default_config()
    if created:
        print(f"config: {cfg_path} (installed)")
    else:
        print(f"config: {cfg_path} (already present)")
    print()
    return cmd_check(args)


def _require_models_ready(cfg) -> int | None:
    """Return exit code 2 if offline prerequisites are not met; None if ok."""
    if all_models_cached(cfg):
        return None
    print(models_prereq_help(cfg), file=sys.stderr)
    for name, ok, detail in models_status(cfg):
        state = "ready" if ok else "missing"
        print(f"  {name} ({detail}): {state}", file=sys.stderr)
    return 2


def cmd_check(args: argparse.Namespace) -> int:
    try:
        require_ffmpeg()
        print("ffmpeg: ok")
    except FfmpegNotFoundError as e:
        print(e, file=sys.stderr)
        return 2
    try:
        import mlx_whisper  # noqa: F401

        print("mlx-whisper: ok")
    except ImportError:
        print("mlx-whisper: not installed", file=sys.stderr)
        return 2

    if args.skip_model:
        print("transcripto: ready (model check skipped — dev/CI only)")
        return 0

    cfg = load_config(Path(args.config) if args.config else None)
    if getattr(args, "model", None):
        cfg.model = args.model

    if cfg.diarization:
        try:
            check_pyannote_available()
            print("pyannote.audio: ok")
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 2

    models_ok = True
    for name, ok, detail in models_status(cfg):
        state = "ready" if ok else "not ready"
        print(f"model {name} ({detail}): {state}")
        if not ok:
            models_ok = False

    if not models_ok:
        if getattr(args, "verbose", False):
            print(models_status_verbose(cfg), file=sys.stderr)
        print(models_prereq_help(cfg), file=sys.stderr)
        return 2

    if cfg.diarization:
        print(f"diarization: enabled ({cfg.diarization_pipeline})")
    else:
        print("diarization: disabled")

    print("transcripto: ready (offline — local models verified)")
    return 0


def resolve_transcribe_path(parts: list[str]) -> Path:
    """Join path parts split by the shell when the user omits quotes around spaces."""
    if not parts:
        raise SystemExit("transcribe: missing path")
    if len(parts) == 1:
        return Path(parts[0]).expanduser().resolve()
    return Path(*parts).expanduser().resolve()


def _apply_transcribe_overrides(cfg, args: argparse.Namespace) -> None:
    if args.model:
        cfg.model = args.model
    if args.language:
        cfg.language = args.language
    if args.output_mode:
        cfg.output_mode = OutputMode(args.output_mode)
    if args.output_dir:
        cfg.output_dir = Path(args.output_dir).expanduser()
    if args.formats:
        cfg.formats = [f.strip() for f in args.formats.split(",")]
    if getattr(args, "no_diarization", False):
        cfg.diarization = False


def cmd_transcribe(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    cfg = load_config(Path(args.config) if args.config else None)
    _apply_transcribe_overrides(cfg, args)

    err = _require_models_ready(cfg)
    if err is not None:
        return err

    path = resolve_transcribe_path(args.path)
    extensions = cfg.watch_extensions
    exclude = (
        cfg.output_dir.resolve()
        if cfg.output_mode == OutputMode.ARCHIVE
        else None
    )
    videos = discover_videos(
        path,
        extensions=extensions,
        recursive=args.recursive,
        exclude_under=exclude,
    )
    input_root = path if path.is_dir() else path.parent
    return run_batch(
        videos,
        cfg,
        force=args.force,
        verbose=args.verbose,
        input_root=input_root,
    )


def cmd_watch(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    cfg = load_config(Path(args.config) if args.config else None)
    if args.model:
        cfg.model = args.model
    if getattr(args, "no_diarization", False):
        cfg.diarization = False
    err = _require_models_ready(cfg)
    if err is not None:
        return err
    return run_watch(cfg, force=args.force, verbose=args.verbose)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="transcripto")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser(
        "init",
        help="Install default config at ~/.config/transcripto/config.yaml",
    )
    init_p.add_argument(
        "--config",
        type=str,
        default=None,
        help="Destination path (default: ~/.config/transcripto/config.yaml)",
    )
    init_p.add_argument(
        "--force",
        action="store_true",
        help="Replace existing config with the bundled default",
    )
    init_p.set_defaults(func=cmd_init)

    setup_p = sub.add_parser(
        "setup",
        help="Install config and verify offline prerequisites",
    )
    setup_p.add_argument("--config", type=str, default=None)
    setup_p.add_argument("--model", type=str, default=None)
    setup_p.add_argument("--no-diarization", action="store_true")
    setup_p.add_argument(
        "--skip-model",
        action="store_true",
        help="Skip model cache check (dev/CI only)",
    )
    setup_p.add_argument(
        "--verbose",
        action="store_true",
        help="Show hub cache paths when model check fails",
    )
    setup_p.set_defaults(func=cmd_setup)

    check_p = sub.add_parser(
        "check",
        help="Verify ffmpeg, deps, and locally cached models (offline only)",
    )
    check_p.add_argument("--config", type=str, default=None)
    check_p.add_argument("--model", type=str, default=None)
    check_p.add_argument(
        "--skip-model",
        action="store_true",
        help="Skip model cache check (dev/CI only)",
    )
    check_p.add_argument(
        "--verbose",
        action="store_true",
        help="Show hub cache paths and why a model is not ready",
    )
    check_p.set_defaults(func=cmd_check)

    tr = sub.add_parser("transcribe", help="Transcribe file or directory")
    tr.add_argument(
        "path",
        nargs="+",
        help="File or directory (quote paths with spaces, or omit quotes to auto-join)",
    )
    tr.add_argument("--config", type=str, default=None)
    tr.add_argument("--force", action="store_true")
    tr.add_argument("--recursive", action="store_true", default=True)
    tr.add_argument("--no-recursive", action="store_false", dest="recursive")
    tr.add_argument(
        "--output-mode",
        choices=["archive", "beside", "mirror", "flat"],
    )
    tr.add_argument("--output-dir", type=str)
    tr.add_argument("--model", type=str)
    tr.add_argument("--language", type=str)
    tr.add_argument("--formats", type=str, help="txt,srt,vtt,json")
    tr.add_argument("--verbose", action="store_true")
    tr.add_argument(
        "--no-diarization",
        action="store_true",
        help="Disable speaker diarization for this run",
    )
    tr.set_defaults(func=cmd_transcribe)

    watch_p = sub.add_parser("watch", help="Watch folders for new videos")
    watch_p.add_argument("--config", type=str, default=None)
    watch_p.add_argument("--force", action="store_true")
    watch_p.add_argument("--model", type=str)
    watch_p.add_argument("--verbose", action="store_true")
    watch_p.add_argument(
        "--no-diarization",
        action="store_true",
        help="Disable speaker diarization for this run",
    )
    watch_p.set_defaults(func=cmd_watch)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if is_runtime_command(args.command):
        apply_runtime_offline_env()
    code = args.func(args)
    raise SystemExit(code)
