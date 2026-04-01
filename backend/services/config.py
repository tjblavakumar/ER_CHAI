"""Config loader for the FRBSF Chart Builder application."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from backend.models.schemas import AppConfig


class ConfigError(Exception):
    """Raised when the configuration file is missing, unreadable, or invalid."""


def load_config(path: str = "config.yaml") -> AppConfig:
    """Load config from a YAML file and return a validated AppConfig.

    Raises ``ConfigError`` with a descriptive message when:
    - The file does not exist or cannot be read.
    - The YAML content is not a valid mapping.
    - Required keys are missing or values are malformed.
    """
    config_path = Path(path)

    # --- File existence ---
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {path}")

    # --- Read & parse YAML ---
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Unable to read config file {path}: {exc}") from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Malformed YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(
            f"Config file {path} must contain a YAML mapping, got {type(data).__name__}"
        )

    # --- Validate via Pydantic ---
    try:
        return AppConfig(**data)
    except ValidationError as exc:
        missing_keys: list[str] = []
        malformed_keys: list[str] = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            if error["type"] == "missing":
                missing_keys.append(field)
            else:
                malformed_keys.append(field)

        parts: list[str] = []
        if missing_keys:
            parts.append(f"missing keys: {', '.join(missing_keys)}")
        if malformed_keys:
            parts.append(f"malformed keys: {', '.join(malformed_keys)}")

        detail = "; ".join(parts) if parts else str(exc)
        raise ConfigError(f"Invalid configuration in {path} — {detail}") from exc
