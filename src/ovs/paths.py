import shutil
from enum import Enum
from pathlib import Path


class OutputMode(str, Enum):
    BESIDE = "beside"
    MIRROR = "mirror"
    FLAT = "flat"
    ARCHIVE = "archive"


def effective_output_formats(formats: list[str]) -> list[str]:
    """TXT is derived from VTT; include it whenever VTT is requested."""
    result = list(formats)
    if "vtt" in result and "txt" not in result:
        result.append("txt")
    return result


def archive_dir_for(video: Path, output_dir: Path) -> Path:
    """
    Per-video folder under output_dir (e.g. ~/Transcripts/recording/).

    Uses the video stem; appends -2, -3, … if that folder name already exists.
    """
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / video.stem
    if video.parent.resolve() == base.resolve():
        return base
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = output_dir / f"{video.stem}-{n}"
        if not candidate.exists():
            return candidate
        n += 1


def output_paths_for(
    video_path: Path,
    *,
    output_mode: OutputMode,
    output_dir: Path,
    formats: list[str],
    mirror_root: Path | None = None,
) -> dict[str, Path]:
    stem = video_path.stem
    paths: dict[str, Path] = {}
    for fmt in formats:
        if output_mode == OutputMode.BESIDE:
            paths[fmt] = video_path.parent / f"{stem}.{fmt}"
        elif output_mode == OutputMode.FLAT:
            paths[fmt] = output_dir / f"{stem}.{fmt}"
        elif output_mode == OutputMode.MIRROR:
            if mirror_root is None:
                raise ValueError("mirror_root required for mirror mode")
            rel = video_path.relative_to(mirror_root)
            paths[fmt] = output_dir / rel.with_suffix(f".{fmt}")
        elif output_mode == OutputMode.ARCHIVE:
            folder = archive_dir_for(video_path, output_dir)
            paths[fmt] = folder / f"{stem}.{fmt}"
        else:
            raise ValueError(f"unknown output mode: {output_mode}")
    return paths


def archived_video_path(video_path: Path, output_paths: dict[str, Path]) -> Path:
    """Destination path for the video inside the archive folder."""
    if not output_paths:
        raise ValueError("output_paths required")
    return next(iter(output_paths.values())).parent / video_path.name


def should_skip(
    paths: dict[str, Path],
    *,
    formats: list[str],
    force: bool = False,
    video_path: Path | None = None,
    output_mode: OutputMode | None = None,
) -> bool:
    if force:
        return False
    if not all(paths[fmt].exists() for fmt in formats):
        return False
    if output_mode == OutputMode.ARCHIVE and video_path is not None:
        return archived_video_path(video_path, paths).exists()
    return True


def move_video_to_archive(video_path: Path, output_paths: dict[str, Path]) -> Path:
    """Move the source video into the archive folder after transcripts are written."""
    dest = archived_video_path(video_path, output_paths)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if video_path.resolve() == dest.resolve():
        return dest
    shutil.move(str(video_path), str(dest))
    return dest
