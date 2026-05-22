"""Enforce offline Hugging Face hub access for OVS runtime commands."""

from __future__ import annotations

import os

from ovs.xdg import apply_hf_env_defaults

_RUNTIME_OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
}

# CLI subcommands that only verify or run on local cache (no HF network).
RUNTIME_COMMANDS = frozenset({"init", "setup", "check", "transcribe", "watch"})


def apply_runtime_offline_env() -> None:
    """Set HF cache paths and hub offline flags for the current process (idempotent)."""
    apply_hf_env_defaults()
    os.environ.update(_RUNTIME_OFFLINE_ENV)


def is_runtime_command(command: str | None) -> bool:
    return command in RUNTIME_COMMANDS
