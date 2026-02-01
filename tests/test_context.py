"""Tests for CLIContext."""

import os
import tempfile

import yaml

from aceteam_nodes.context import CLIContext


def test_cli_context_loads_empty_config():
    ctx = CLIContext(config_path="/nonexistent/config.yaml")
    assert ctx.config == {}


def test_cli_context_loads_config():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"default_model": "claude-3-5-sonnet-latest"}, f)
        f.flush()
        try:
            ctx = CLIContext(config_path=f.name)
            assert ctx.config["default_model"] == "claude-3-5-sonnet-latest"
        finally:
            os.unlink(f.name)


def test_cli_context_verbose_flag():
    ctx = CLIContext(config_path="/nonexistent/config.yaml", verbose=True)
    assert ctx.verbose is True

    ctx = CLIContext(config_path="/nonexistent/config.yaml", verbose=False)
    assert ctx.verbose is False
