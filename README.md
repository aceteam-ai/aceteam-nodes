# aceteam-nodes

[![PyPI version](https://img.shields.io/pypi/v/aceteam-nodes.svg)](https://pypi.org/project/aceteam-nodes/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

A bundle of workflow node types for [aceteam-workflow-engine](https://github.com/adanomad/workflow-engine):
LLM text generation, HTTP requests, authenticated browser fetch, and XPath
extraction.

This is a **node-source package**, not a runner. It ships no CLI and no execution
engine — it advertises its nodes through the `aceteam_workflow_engine.nodes`
entry-point group, and an operator mounts them into an engine with
`wengine install aceteam-nodes`. The engine then executes them.

## Install into a workflow engine

Nodes are discovered through entry points and mounted by the engine operator with
the `wengine` CLI (which drives `uv` under the hood). From an engine project:

```bash
# Create an engine project if you don't have one yet
wengine init  # creates engine.yaml + a pyproject.toml to install into

# Mount every node this package exposes
wengine install aceteam-nodes

# ...or mount only specific nodes
wengine install aceteam-nodes --only LLM --only APICall
```

`wengine install` runs `uv add aceteam-nodes` and records each node in the
operator-controlled name map (`engine.yaml`). It reads the entry-point table from
package metadata — listed below — without importing the modules. Nodes whose
entry declares an extra (e.g. `LLM [llm]`) pull that optional dependency
automatically, so `wengine install aceteam-nodes --only LLM` installs
`aceteam-nodes[llm]`.

Workflows then reference these nodes by their `type` discriminator (`LLM`,
`APICall`, …). See the engine's [node-distribution docs](https://github.com/adanomad/workflow-engine/blob/main/docs/node-distribution.md)
for the full install/uninstall surface and the trust model.

### Direct install

To add the package (and its optional deps) to an environment directly:

```bash
pip install aceteam-nodes                  # core nodes only
pip install "aceteam-nodes[llm]"           # + LLM (aceteam-aep)
pip install "aceteam-nodes[browser-fetch]" # + BrowserFetch (Playwright)
pip install "aceteam-nodes[xpath-extract]" # + XPathExtract (lxml)
```

<details>
<summary>Using <code>uv</code></summary>

```bash
uv add aceteam-nodes                  # core nodes only
uv add "aceteam-nodes[llm]"           # + LLM (aceteam-aep)
uv add "aceteam-nodes[browser-fetch]" # + BrowserFetch (Playwright)
uv add "aceteam-nodes[xpath-extract]" # + XPathExtract (lxml)
```

</details>

## Available Nodes

| Node                                                                                  | Extra           | Description                                                                 |
| ------------------------------------------------------------------------------------- | --------------- | --------------------------------------------------------------------------- |
| LLM                                                                                   | `llm`           | AI text generation via aceteam-aep (OpenAI, Anthropic, Google, xAI, Ollama) |
| APICall                                                                               | —               | HTTP requests with Jinja templating                                         |
| BrowserFetch                                                                          | `browser-fetch` | Authenticated web fetch via Playwright                                      |
| XPathExtract                                                                          | `xpath-extract` | XPath extraction over HTML/XML                                              |

Each node needing a heavy/optional dependency has **one extra named after the
node** (`llm`, `browser-fetch`, `xpath-extract`), so `aceteam-nodes[browser-fetch]`
reads as "BrowserFetch is installed." The APICall node needs no extra.

## Browser profile setup

`BrowserFetch` drives a real Chromium profile so it can fetch authenticated pages.
After installing the `browser-fetch` extra and Playwright's browser binaries,
create the profile interactively:

```bash
# After: pip install "aceteam-nodes[browser-fetch]" && playwright install chromium
ace-browser-setup
# equivalent: uv run python scripts/browser_setup.py
```

## Configuration

LLM provider credentials are read from the environment:

```bash
export OPENAI_API_KEY=sk-...
# or
export ANTHROPIC_API_KEY=sk-ant-...
```

## Development

```bash
# Setup (installs project + dev group: pyright, pytest, ruff, aceteam-aep, playwright, lxml)
uv sync --group dev

# Test
uv run pytest
uv run pytest -x                   # stop on first failure

# Lint & format
uv run ruff check && uv run ruff format

# Type check
uv run pyright

# Build
uv build

# Release
scripts/release.sh -v vX.Y.Z --dry-run   # preview
scripts/release.sh -v vX.Y.Z -y          # publish to PyPI + GitHub
```

### Adding a node

Add three things in lockstep:

1. The node class in `src/aceteam_nodes/nodes/` (with its `TYPE_INFO`).
2. The export in `nodes/__init__.py`.
3. The export in `__init__.py`.
4. The entry-point line under `[project.entry-points."aceteam_workflow_engine.nodes"]` in `pyproject.toml` (append `[extra_dependency_name]` if it needs an optional dependency).

## Related

- **[Workflow Engine](https://github.com/adanomad/workflow-engine)** — the DAG execution engine that discovers and runs these nodes
- **[aceteam-aep](https://pypi.org/project/aceteam-aep/)** — multi-provider LLM abstraction used by the LLM node

## License

MIT
