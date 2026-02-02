# aceteam-nodes

[![PyPI version](https://img.shields.io/pypi/v/aceteam-nodes.svg)](https://pypi.org/project/aceteam-nodes/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

AceTeam workflow nodes for local CLI execution. Run AceTeam workflows on your own machine with any LLM provider.

## Install

```bash
pip install aceteam-nodes
```

## Quick Start

```bash
# Run a workflow
python -m aceteam_nodes.cli run examples/hello-llm.json --input '{"prompt":"Explain AI in one sentence"}'

# List available nodes
python -m aceteam_nodes.cli list-nodes

# Validate a workflow file
python -m aceteam_nodes.cli validate examples/hello-llm.json
```

## Configuration

Create `~/.ace/config.yaml` to configure API keys and defaults:

```yaml
default_model: gpt-4o-mini
```

Set your API key via environment variable:

```bash
export OPENAI_API_KEY=sk-...
# or
export ANTHROPIC_API_KEY=sk-ant-...
```

## How It Works

```
Workflow JSON ──> AceTeamWorkflow (load + validate)
                       │
                       ▼
              workflow-engine (DAG execution)
                       │
                       ▼
              AceTeamNode.run() per node
                  │         │
                  ▼         ▼
              litellm    httpx/jinja2
            (100+ LLMs)  (API calls)
```

1. A workflow JSON file defines nodes and their connections as a directed acyclic graph
2. `AceTeamWorkflow` validates the file and resolves node references
3. The `aceteam-workflow-engine` executes nodes in topological order
4. Each node type implements `run()` — LLM nodes call litellm, API nodes use httpx, etc.
5. Results flow through the graph until all outputs are produced

## Available Nodes

| Node | Description |
|------|-------------|
| LLM | AI text generation via litellm (100+ providers) |
| APICall | HTTP requests with Jinja templating |
| TextInput | Static text source |
| DataTransform | Data transformation |
| CSVReader | CSV data source |
| If / IfElse | Conditional branching |
| ForEach | Loop iteration |
| Equal, NotEqual, GreaterThan, LessThan, And, Or, Not | Comparison/logic operators |

## Development

```bash
# Setup
uv sync --extra dev

# Test
uv run pytest

# Lint & format
uv run ruff check && uv run ruff format

# Type check
uv run pyright

# Build
uv build
```

## Related

- **[Ace CLI](https://github.com/aceteam-ai/ace)** — TypeScript CLI that wraps this package for a streamlined user experience
- **[Workflow Engine](https://github.com/adanomad/workflow-engine)** — The DAG execution engine used under the hood

## License

MIT
