"""Workflow execution for CLI context."""

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from workflow_engine import Workflow, WorkflowEngine
from workflow_engine.execution import TopologicalExecutionAlgorithm

from .context import CLIContext
from .nodes import aceteam_node_registry
from .utils import dump_data_mapping

logger = logging.getLogger(__name__)


class WorkflowFileNotFoundError(Exception):
    pass


class WorkflowDeserializationError(Exception):
    pass


def load_workflow_from_file(file_path: str) -> Workflow:
    """Load a workflow from a JSON file."""
    # Import nodes to trigger auto-registration before deserialization
    path = Path(file_path)
    if not path.exists():
        raise WorkflowFileNotFoundError(f"Workflow file not found: {file_path}")

    with open(path) as f:
        data = json.load(f)

    try:
        return Workflow.model_validate(data)
    except ValidationError as e:
        raise WorkflowDeserializationError(f"Invalid workflow file: {e}") from e


async def run_workflow_from_file(
    file_path: str,
    input: Mapping[str, Any] | None = None,
    *,
    config_path: str = "~/.ace/config.yaml",
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Load and execute a workflow from a JSON file.

    Returns a dict with the workflow output values.
    """

    engine = WorkflowEngine(
        node_registry=aceteam_node_registry,
        execution_algorithm=TopologicalExecutionAlgorithm(),
    )
    workflow = engine.load(load_workflow_from_file(file_path))
    context = CLIContext(
        config_path=config_path,
        verbose=verbose,
    )
    errors, output_values = await engine.execute(
        context=context,
        workflow=workflow,
        input=input or {},
    )

    output = dump_data_mapping(output_values)

    if errors.workflow_errors or errors.node_errors:
        return {
            "success": False,
            "output": dict(output),
            "errors": errors.model_dump(),
        }

    return {
        "success": True,
        "output": dict(output),
    }


__all__ = [
    "WorkflowDeserializationError",
    "WorkflowFileNotFoundError",
    "load_workflow_from_file",
    "run_workflow_from_file",
]
