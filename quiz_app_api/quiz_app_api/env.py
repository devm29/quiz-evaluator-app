"""Small helpers for reading settings out of the process environment.

Deliberately dependency-free: the project only needs a handful of typed
lookups, which is not enough to justify pulling in django-environ.
"""

from __future__ import annotations

import os

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def env_str(name: str, default: str = "") -> str:
    """Return an environment variable, stripped, falling back to *default*."""
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable.

    Raises ValueError on a value that is neither truthy nor falsy so that a
    typo ("DJANGO_DEBUG=ture") fails loudly at boot instead of silently
    disabling debug mode.
    """
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    normalised = raw.strip().lower()
    if normalised in _TRUE_VALUES:
        return True
    if normalised in _FALSE_VALUES:
        return False
    raise ValueError(
        f"{name}={raw!r} is not a valid boolean; use one of "
        f"{sorted(_TRUE_VALUES | _FALSE_VALUES)}"
    )


def env_int(name: str, default: int) -> int:
    """Parse an integer environment variable, failing loudly on garbage."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name}={raw!r} is not a valid integer") from exc


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Parse a comma-separated environment variable into a list of strings."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return list(default or [])
    return [item.strip() for item in raw.split(",") if item.strip()]
