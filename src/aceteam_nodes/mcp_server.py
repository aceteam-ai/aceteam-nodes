"""ace-local MCP server — run AceTeam workflows locally via Claude Code."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys

from fastmcp import FastMCP

from .discovery import build_full_registry
from .execution import load_workflow_from_file
from .utils import build_data_mapping, dump_data_mapping

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "ace-local",
    instructions=(
        "Run AceTeam workflows locally. List nodes, validate and execute"
        " DAG-based workflows on your machine."
    ),
)

REGISTRY_BASE_URL = (
    "https://raw.githubusercontent.com/aceteam-ai/marketplace/main/registry"
)


@mcp.tool()
async def list_nodes() -> str:
    """List all available workflow node types with their schemas.

    Returns every registered node including core nodes and any installed
    community node packages. Each node includes its input, output, and
    parameter JSON schemas for workflow composition.
    """
    registry = build_full_registry()
    nodes = []
    for type_name, node_cls in registry.all_concrete_node_classes():
        info = node_cls.TYPE_INFO
        entry = {
            "type": type_name,
            "display_name": info.display_name,
            "description": info.description,
            "version": str(info.version),
        }
        try:
            instance = node_cls.model_construct()
            entry["input_schema"] = instance.input_type.model_json_schema()
            entry["output_schema"] = instance.output_type.model_json_schema()
        except Exception:
            pass
        if info.parameter_schema is not None:
            entry["parameter_schema"] = info.parameter_schema.model_dump()
        nodes.append(entry)
    return json.dumps(nodes, indent=2)


@mcp.tool()
async def run_workflow(workflow_json: str, input_json: str = "{}") -> str:
    """Execute a workflow from a JSON file path or inline JSON string.

    Args:
        workflow_json: Path to a workflow .json file, or an inline JSON workflow definition.
        input_json: JSON object with input values for the workflow.
    """
    from workflow_engine import WorkflowEngine
    from workflow_engine.execution import TopologicalExecutionAlgorithm

    from .context import CLIContext

    registry = build_full_registry()
    engine = WorkflowEngine(
        node_registry=registry,
        execution_algorithm=TopologicalExecutionAlgorithm(),
    )

    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError as e:
        return json.dumps({"success": False, "error": f"Invalid input JSON: {e}"})

    try:
        workflow_data = json.loads(workflow_json)
        from workflow_engine import Workflow

        raw_workflow = Workflow.model_validate(workflow_data)
    except (json.JSONDecodeError, ValueError):
        raw_workflow = load_workflow_from_file(workflow_json)

    workflow = engine.load(raw_workflow)
    context = CLIContext()
    input_mapping = build_data_mapping(input_data, workflow.input_fields)

    result = await engine.execute(
        context=context,
        workflow=workflow,
        input=input_mapping,
    )
    output = dump_data_mapping(result.output)

    from workflow_engine import WorkflowExecutionResultStatus

    if result.status == WorkflowExecutionResultStatus.ERROR:
        return json.dumps({
            "success": False,
            "output": output,
            "errors": result.errors.model_dump(),
        })

    return json.dumps({"success": True, "output": output})


@mcp.tool()
async def validate_workflow(workflow_json: str) -> str:
    """Validate a workflow definition without executing it.

    Checks that the DAG structure is valid, all node types exist, and
    edge types are compatible.

    Args:
        workflow_json: Path to a workflow .json file, or an inline JSON workflow definition.
    """
    from workflow_engine import WorkflowEngine
    from workflow_engine.execution import TopologicalExecutionAlgorithm

    registry = build_full_registry()
    engine = WorkflowEngine(
        node_registry=registry,
        execution_algorithm=TopologicalExecutionAlgorithm(),
    )

    try:
        workflow_data = json.loads(workflow_json)
        from workflow_engine import Workflow

        raw_workflow = Workflow.model_validate(workflow_data)
    except (json.JSONDecodeError, ValueError):
        raw_workflow = load_workflow_from_file(workflow_json)

    try:
        engine.load(raw_workflow)
        return json.dumps({"valid": True})
    except Exception as e:
        return json.dumps({"valid": False, "error": str(e)})


@mcp.tool()
async def install_nodes(package: str) -> str:
    """Install a community node package into the current environment.

    After installation, the MCP server must be restarted for new nodes
    to appear in list_nodes.

    If running via uvx, use this instead:
        uv tool install --with <package> aceteam-nodes[mcp]

    Args:
        package: PyPI package name to install (e.g. 'aceteam-email-nodes').
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return json.dumps({
                "success": False,
                "error": proc.stderr.strip(),
                "hint": "If running via uvx, installations don't persist across restarts. "
                "Use instead: uv tool install --with "
                + package
                + " aceteam-nodes[mcp]",
            })
        is_uvx = "UV_TOOL_DIR" in os.environ
        restart_note = (
            f"Installed {package}. Restart the MCP server to load new nodes."
            if not is_uvx
            else f"Installed {package} into the current environment. "
            "Note: if this server runs via uvx, this installation won't persist. "
            f"For permanent install, run: uv tool install --with {package} aceteam-nodes[mcp]"
        )
        return json.dumps({"success": True, "message": restart_note})
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "error": "Installation timed out after 120s"})


@mcp.tool()
async def search_registry(query: str) -> str:
    """Search the community node registry for packages matching a query.

    Searches package names, descriptions, node names, and keywords.

    Args:
        query: Search term (e.g. 'email', 'gmail', 'fireflies').
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{REGISTRY_BASE_URL}/_index.json", timeout=10)
            resp.raise_for_status()
            index = resp.json()

            results = []
            query_lower = query.lower()
            for filename in index:
                entry_resp = await client.get(
                    f"{REGISTRY_BASE_URL}/{filename}", timeout=10
                )
                if entry_resp.status_code != 200:
                    continue
                entry = entry_resp.json()
                searchable = " ".join([
                    entry.get("name", ""),
                    entry.get("description", ""),
                    " ".join(entry.get("nodes", [])),
                    " ".join(entry.get("keywords", [])),
                ]).lower()
                if query_lower in searchable:
                    results.append(entry)

            return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Registry search failed: {e}"})


def main():
    mcp.run()


if __name__ == "__main__":
    main()
