import os
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

import yaml

from ovs.paths import OutputMode

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "ovs" / "config.yaml"
_BUNDLED_EXAMPLE = "config.yaml.example"


def bundled_config_example_text() -> str:
    """Commented default config shipped with the package."""
    pkg_dir = Path(__file__).resolve().parent
    repo_example = pkg_dir.parent.parent / "config" / "config.yaml.example"
    for candidate in (pkg_dir / _BUNDLED_EXAMPLE, repo_example):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return files("ovs").joinpath(_BUNDLED_EXAMPLE).read_text(encoding="utf-8")


def default_config_dict() -> dict:
    """Defaults parsed from the bundled example (kept in sync with init)."""
    data = yaml.safe_load(bundled_config_example_text()) or {}
    watch = data.get("watch") or {}
    return {
        "model": data.get("model", "medium"),
        "language": data.get("language", "auto"),
        "output_mode": data.get("output_mode", "archive"),
        "output_dir": data.get("output_dir", str(Path.home() / "Transcripts")),
        "formats": list(data.get("formats", ["vtt"])),
        "diarization": bool(data.get("diarization", True)),
        "diarization_pipeline": data.get(
            "diarization_pipeline", "pyannote/speaker-diarization-community-1"
        ),
        "watch": {
            "paths": watch.get("paths", [str(Path.home() / "Movies")]),
            "debounce_seconds": watch.get("debounce_seconds", 2),
            "extensions": watch.get("extensions", [".mov", ".mp4"]),
        },
    }


@dataclass
class AppConfig:
    model: str = "medium"
    language: str = "auto"
    output_mode: OutputMode = OutputMode.ARCHIVE
    output_dir: Path = field(default_factory=lambda: Path.home() / "Transcripts")
    formats: list[str] = field(default_factory=lambda: ["vtt"])
    diarization: bool = True
    diarization_pipeline: str = "pyannote/speaker-diarization-community-1"
    watch_paths: list[Path] = field(default_factory=list)
    watch_debounce_seconds: float = 2.0
    watch_extensions: list[str] = field(default_factory=lambda: [".mov", ".mp4"])


def load_config(path: Path | None = None) -> AppConfig:
    cfg_path = path or Path(
        os.environ.get("OVS_CONFIG", DEFAULT_CONFIG_PATH)
    )
    data = default_config_dict()
    if cfg_path.exists():
        loaded = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        data.update(loaded)
    watch = data.get("watch") or {}
    return AppConfig(
        model=data["model"],
        language=data["language"],
        output_mode=OutputMode(data["output_mode"]),
        output_dir=Path(data["output_dir"]).expanduser(),
        formats=list(data["formats"]),
        diarization=bool(data.get("diarization", True)),
        diarization_pipeline=str(
            data.get("diarization_pipeline", "pyannote/speaker-diarization-community-1")
        ),
        watch_paths=[Path(p).expanduser() for p in watch.get("paths", [])],
        watch_debounce_seconds=float(watch.get("debounce_seconds", 2)),
        watch_extensions=list(watch.get("extensions", [".mov", ".mp4"])),
    )


def write_default_config(
    path: Path | None = None, *, force: bool = False
) -> tuple[Path, bool]:
    """
    Install bundled config.yaml to the user config path.

    Returns (path, created). created is False when the file already exists and
    force was not set.
    """
    cfg_path = path or DEFAULT_CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if cfg_path.exists() and not force:
        return cfg_path, False
    cfg_path.write_text(bundled_config_example_text(), encoding="utf-8")
    return cfg_path, True
