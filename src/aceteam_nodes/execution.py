"""Workflow execution for CLI context."""

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from workflow_engine import Workflow, WorkflowEngine, WorkflowExecutionResultStatus
from workflow_engine.core import ValidatedWorkflow
from workflow_engine.execution import ParallelExecutionAlgorithm

from .context import CLIContext
from .nodes import aceteam_node_registry
from .utils import dump_data_mapping

logger = logging.getLogger(__name__)


engine = WorkflowEngine(
    node_registry=aceteam_node_registry,
    execution_algorithm=ParallelExecutionAlgorithm(),
)


class WorkflowFileNotFoundError(Exception):
    pass


class WorkflowDeserializationError(Exception):
    pass


async def load_workflow_from_file(file_path: str) -> ValidatedWorkflow:
    """Load a workflow from a JSON file."""
    # Import nodes to trigger auto-registration before deserialization
    path = Path(file_path)
    if not path.exists():
        raise WorkflowFileNotFoundError(f"Workflow file not found: {file_path}")

    with open(path) as f:
        data = json.load(f)

    try:
        raw_workflow = Workflow.model_validate(data)
    except ValidationError as e:
        raise WorkflowDeserializationError(f"Invalid workflow file: {e}") from e

    return await engine.validate(raw_workflow)


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
    workflow = await load_workflow_from_file(file_path)
    context = CLIContext(
        config_path=config_path,
        verbose=verbose,
    )
    if input is None:
        input = {}
    result = await engine.execute(
        context=context,
        workflow=workflow,
        input=input,
    )

    output = dump_data_mapping(result.output)

    if result.status == WorkflowExecutionResultStatus.ERROR:
        return {
            "success": False,
            "output": output,
            "errors": result.errors.model_dump(),
        }

    return {
        "success": True,
        "output": output,
    }


__all__ = [
    "WorkflowDeserializationError",
    "WorkflowFileNotFoundError",
    "load_workflow_from_file",
    "run_workflow_from_file",
]
