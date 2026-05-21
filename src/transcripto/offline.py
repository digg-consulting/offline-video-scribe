"""Enforce offline Hugging Face hub access for transcripto runtime commands."""

from __future__ import annotations

import os

_RUNTIME_OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
}

# CLI subcommands that only verify or run on local cache (no HF network).
RUNTIME_COMMANDS = frozenset({"init", "setup", "check", "transcribe", "watch"})


def apply_runtime_offline_env() -> None:
    """Set hub offline flags for the current process (idempotent)."""
    os.environ.update(_RUNTIME_OFFLINE_ENV)


def is_runtime_command(command: str | None) -> bool:
    return command in RUNTIME_COMMANDS
