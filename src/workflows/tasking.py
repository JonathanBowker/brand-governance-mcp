"""Helpers for optional FastMCP background task support."""

from importlib.util import find_spec

from fastmcp.server.tasks.config import TaskConfig


def supports_background_tasks() -> bool:
    """Return True when the FastMCP task runtime is installed."""
    return find_spec("pydocket") is not None


def optional_task_config() -> bool | TaskConfig:
    """Return an optional task config when task runtime support is available."""
    if supports_background_tasks():
        return TaskConfig(mode="optional")
    return False
