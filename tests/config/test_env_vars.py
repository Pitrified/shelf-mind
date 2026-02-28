"""Test that the environment variables are available."""

import os


def test_env_vars() -> None:
    """The environment var SHELF_MIND_SAMPLE_ENV_VAR is available."""
    assert "SHELF_MIND_SAMPLE_ENV_VAR" in os.environ
    assert os.environ["SHELF_MIND_SAMPLE_ENV_VAR"] == "sample"
