# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`aceteam-nodes` is a Python package that publishes a bundle of workflow node types (LLM, HTTP, browser fetch, XPath extraction) for `aceteam-workflow-engine`. It is a **node-source package**, not a runner: it ships no CLI and no execution engine. It advertises its nodes through the `aceteam_workflow_engine.nodes` entry-point group, and an operator mounts them into an engine with `wengine install aceteam-nodes`.

The package uses `aceteam-aep` for multi-provider LLM support (OpenAI, Anthropic, Google, xAI, Ollama) via direct SDK calls, and depends on `aceteam-workflow-engine` for the `Node` base class and value types.

## Development Commands

```bash
# Setup
uv sync --group dev               # Install project + dev group (pyright, pytest, ruff, aceteam-aep, playwright, lxml)

# Browser profile (Playwright; for BrowserFetch)
ace-browser-setup                 # console script
# or: uv run python scripts/browser_setup.py

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
├── __init__.py            # Public API + __version__ (re-exports node classes)
├── browser_setup.py       # Interactive Chromium profile setup for BrowserFetch (ace-browser-setup)
├── playwright_profile.py  # Playwright profile location/management helpers
├── context.py             # CLIContext — a LocalContext subclass (model, API keys)
├── utils.py               # Shared utilities
└── nodes/                 # Node type implementations
    ├── __init__.py        # Re-exports node classes
    ├── api_call.py        # HTTP requests with Jinja templating (APICall)
    ├── browser_fetch.py   # Authenticated web fetch via Playwright (BrowserFetch)
    ├── xpath_extract.py   # XPath extraction over HTML/XML (XPathExtract)
    └── llm.py             # AI text generation via aceteam-aep (LLM)
```

### Key Dependencies

- `aceteam-workflow-engine` — provides the `Node` base class, value types, and the engine that runs these nodes
- `aceteam-aep` — multi-provider LLM abstraction (direct SDK calls); `llm` extra
- `httpx` — async HTTP client (APICall)
- `jinja2` — template rendering (APICall)
- `pydantic` — data validation
- `playwright` / `playwright-stealth` — `browser-fetch` extra (BrowserFetch)
- `lxml` — `xpath-extract` extra (XPathExtract)

### How node distribution works

The engine discovers nodes **only** through the `aceteam_workflow_engine.nodes` entry-point group declared in `pyproject.toml` — there is no import-time auto-registration. Each entry maps a node's `type` discriminator (e.g. `LLM`) to its `module:Class`, with an optional `[extra]` suffix naming the optional-dependency that node needs (e.g. `LLM = "...:LLMNode [llm]"`). An operator runs `wengine install aceteam-nodes` (or hand-edits their `engine.yaml`) to mount these into an engine; the engine reads the table from package metadata without importing the modules. See `aceteam-workflow-engine`'s `docs/node-distribution.md`.

When adding a node, add four things in lockstep: the class (with its `TYPE_INFO`), the export in `nodes/__init__.py`, the export in `__init__.py`, and the entry-point line in `pyproject.toml`.

### Conventions for extras

Each node needing a heavy/optional dependency gets **one extra named after the node** (`browser-fetch`, `xpath-extract`, `llm`), so a `pyproject.toml` line like `aceteam-nodes[browser-fetch]` reads as "BrowserFetch is installed." The APICall node needs no extra (its deps are core).

## Conventions

- Python 3.12+ required
- Ruff for linting and formatting (line length 100)
- Pyright for type checking (basic mode)
- pytest with asyncio auto mode
- All node types go in `nodes/` and extend `workflow_engine.Node`
- Version is tracked in both `pyproject.toml` and `__init__.py`
