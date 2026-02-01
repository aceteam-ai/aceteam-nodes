# aceteam-nodes

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

## License

MIT
