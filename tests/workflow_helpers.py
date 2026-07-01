"""Helpers for executing a single node inside a minimal workflow."""

from collections.abc import Mapping
from typing import Any

from workflow_engine import (
    Edge,
    ExecutionContext,
    Workflow,
    WorkflowEngine,
    WorkflowExecutionResult,
)
from workflow_engine.core.values import ValueType


def build_single_node_workflow(
    engine: WorkflowEngine,
    node_cls: type,
    *,
    node_id: str = "node",
    params: Mapping[str, Any] | None = None,
    input_fields: Mapping[str, ValueType],
    output_fields: Mapping[str, ValueType],
) -> Workflow:
    input_node = engine.create_input_node(**input_fields)
    output_node = engine.create_output_node(**output_fields)
    node = engine.create_node(node_cls, id=node_id, params=dict(params or {}))
    edges = [
        Edge.from_nodes(source=input_node, source_key=key, target=node, target_key=key)
        for key in input_fields
    ] + [
        Edge.from_nodes(source=node, source_key=key, target=output_node, target_key=key)
        for key in output_fields
    ]
    return Workflow(
        input_node=input_node,
        output_node=output_node,
        inner_nodes=[node],
        edges=edges,
    )


async def execute_single_node(
    engine: WorkflowEngine,
    context: ExecutionContext,
    node_cls: type,
    *,
    node_id: str = "node",
    params: Mapping[str, Any] | None = None,
    input_fields: Mapping[str, ValueType],
    output_fields: Mapping[str, ValueType],
    input: Mapping[str, Any],
) -> WorkflowExecutionResult:
    workflow = build_single_node_workflow(
        engine,
        node_cls,
        node_id=node_id,
        params=params,
        input_fields=input_fields,
        output_fields=output_fields,
    )
    return await engine.execute(context=context, workflow=workflow, input=input)


def error_messages(result: WorkflowExecutionResult) -> list[str]:
    messages: list[str] = []
    for error in result.errors.workflow_errors:
        if error is not None:
            messages.append(error.message)
    for errors in result.errors.node_errors.values():
        for error in errors:
            if error is not None:
                messages.append(error.message)
    return messages
