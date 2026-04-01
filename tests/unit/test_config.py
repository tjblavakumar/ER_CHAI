"""Unit tests for the Config Loader."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.models.schemas import AppConfig
from backend.services.config import ConfigError, load_config


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_load_valid_config(tmp_dir: str) -> None:
    """A fully-specified config file should produce a matching AppConfig."""
    cfg_path = Path(tmp_dir) / "config.yaml"
    cfg_path.write_text(
        "fred_api_key: my-key\n"
        "aws_region: us-east-1\n"
        "bedrock_model_id: anthropic.claude-3-sonnet-20240229-v1:0\n"
        "bedrock_vision_model_id: anthropic.claude-3-sonnet-20240229-v1:0\n"
    )

    config = load_config(str(cfg_path))

    assert isinstance(config, AppConfig)
    assert config.fred_api_key == "my-key"
    assert config.aws_region == "us-east-1"
    assert config.aws_access_key_id is None
    assert config.aws_secret_access_key is None


def test_load_config_with_optional_aws_keys(tmp_dir: str) -> None:
    """Optional AWS credential fields should be populated when present."""
    cfg_path = Path(tmp_dir) / "config.yaml"
    cfg_path.write_text(
        "fred_api_key: key\n"
        "aws_region: eu-west-1\n"
        "aws_access_key_id: AKIAEXAMPLE\n"
        "aws_secret_access_key: secret123\n"
    )

    config = load_config(str(cfg_path))

    assert config.aws_access_key_id == "AKIAEXAMPLE"
    assert config.aws_secret_access_key == "secret123"


def test_load_config_defaults(tmp_dir: str) -> None:
    """Default model IDs should be applied when not specified."""
    cfg_path = Path(tmp_dir) / "config.yaml"
    cfg_path.write_text("fred_api_key: k\naws_region: us-west-2\n")

    config = load_config(str(cfg_path))

    assert config.bedrock_model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
    assert config.bedrock_vision_model_id == "anthropic.claude-3-sonnet-20240229-v1:0"


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


def test_missing_file_raises_config_error() -> None:
    """A non-existent path should raise ConfigError."""
    with pytest.raises(ConfigError, match="not found"):
        load_config("/no/such/file.yaml")


def test_empty_file_raises_config_error(tmp_dir: str) -> None:
    """An empty YAML file (parsed as None) should raise ConfigError."""
    cfg_path = Path(tmp_dir) / "empty.yaml"
    cfg_path.write_text("")

    with pytest.raises(ConfigError, match="mapping"):
        load_config(str(cfg_path))


def test_non_mapping_yaml_raises_config_error(tmp_dir: str) -> None:
    """A YAML file containing a list instead of a mapping should raise ConfigError."""
    cfg_path = Path(tmp_dir) / "list.yaml"
    cfg_path.write_text("- item1\n- item2\n")

    with pytest.raises(ConfigError, match="mapping"):
        load_config(str(cfg_path))


def test_missing_required_key_mentioned_in_error(tmp_dir: str) -> None:
    """Missing required keys should be listed in the error message."""
    cfg_path = Path(tmp_dir) / "partial.yaml"
    cfg_path.write_text("aws_region: us-west-2\n")  # fred_api_key missing

    with pytest.raises(ConfigError, match="fred_api_key"):
        load_config(str(cfg_path))


def test_malformed_yaml_raises_config_error(tmp_dir: str) -> None:
    """Syntactically invalid YAML should raise ConfigError."""
    cfg_path = Path(tmp_dir) / "bad.yaml"
    cfg_path.write_text("fred_api_key: [\n")

    with pytest.raises(ConfigError, match="Malformed YAML"):
        load_config(str(cfg_path))


def test_malformed_value_type_raises_config_error(tmp_dir: str) -> None:
    """A value with the wrong type should be reported as malformed."""
    cfg_path = Path(tmp_dir) / "badtype.yaml"
    # bedrock_model_id expects str, give it a list
    cfg_path.write_text(
        "fred_api_key: k\n"
        "aws_region: us-west-2\n"
        "bedrock_model_id:\n  - a\n  - b\n"
    )

    with pytest.raises(ConfigError, match="malformed keys.*bedrock_model_id"):
        load_config(str(cfg_path))
