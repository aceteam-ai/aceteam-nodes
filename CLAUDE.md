# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`aceteam-nodes` is a Python package that implements workflow node types for local CLI execution. It provides the runtime that powers the `ace` CLI — when a user runs `ace workflow run`, the TypeScript CLI delegates execution to this package via subprocess.

The package uses `litellm` for multi-provider LLM support (OpenAI, Anthropic, Google, and 100+ more) and `aceteam-workflow-engine` for DAG-based workflow graph execution.

## Development Commands

```bash
# Setup
uv sync                           # Install project + dev group (pyright, pytest, ruff, litellm)

# Run
python -m aceteam_nodes.cli run examples/hello-llm.json --input '{"prompt":"Hello"}'
python -m aceteam_nodes.cli list-nodes
python -m aceteam_nodes.cli validate examples/hello-llm.json

# Test
uv run pytest                      # Run all tests
uv run pytest tests/test_nodes.py  # Run specific test file
uv run pytest -x                   # Stop on first failure

# Lint & Format
uv run ruff check                  # Lint
uv run ruff format                 # Format
uv run pyright                     # Type checking

# Build
uv build                           # Creates sdist + wheel in dist/

# Release
./scripts/release.sh -v v0.2.0 --dry-run  # Preview release
./scripts/release.sh -v v0.2.0 -y         # Publish to PyPI + GitHub
```

## Architecture

### Package Structure

```text
src/aceteam_nodes/
├── __init__.py        # Public API + __version__
├── __main__.py        # python -m aceteam_nodes entry point
├── cli.py             # CLI commands (run, validate, list-nodes)
├── context.py         # CLIContext — runtime config (model, API keys)
├── execution.py       # Workflow execution engine bridge
├── utils.py           # Shared utilities
└── nodes/             # Node type implementations
    ├── __init__.py    # Node registration into aceteam_node_registry
    ├── api_call.py    # HTTP requests with Jinja templating
    ├── comparison.py  # Equal, NotEqual, GreaterThan, LessThan, And, Or, Not
    └── llm.py         # AI text generation via litellm
```

### Key Dependencies

- `aceteam-workflow-engine` — DAG execution engine (shared with the platform)
- `litellm` — Multi-provider LLM abstraction
- `httpx` — Async HTTP client (for API call nodes)
- `jinja2` — Template rendering in API call nodes
- `pydantic` — Data validation
- `pyyaml` — Config file parsing

### How It Works

- The CLI loads a workflow JSON file and validates it against the schema
- Each node type (LLM, APICall, etc.) extends `Node` with a `run()` method
- `aceteam-workflow-engine`'s `WorkflowEngine` resolves node references, builds the execution graph, and executes nodes in topological order
- `CLIContext` provides runtime configuration (model, API keys, verbosity)

### Relationship to ace CLI

The `ace` TypeScript CLI is the user-facing tool. It handles:

- Python environment detection and `aceteam-nodes` installation
- Config file management (`~/.ace/config.yaml`)
- Input parsing and output formatting

Execution is delegated to `aceteam-nodes` via `python -m aceteam_nodes.cli`.

## Conventions

- Python 3.12+ required
- Ruff for linting and formatting (line length 100)
- Pyright for type checking (basic mode)
- pytest with asyncio auto mode
- All node types go in `nodes/` directory and extend `AceTeamNode`
- Version is tracked in both `pyproject.toml` and `__init__.py`
