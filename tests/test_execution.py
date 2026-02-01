"""Tests for workflow execution."""

import os
import tempfile

import pytest

from aceteam_nodes.execution import (
    WorkflowDeserializationError,
    WorkflowFileNotFoundError,
    load_workflow_from_file,
    run_workflow_from_file,
)


@pytest.fixture
def text_passthrough_path():
    return os.path.join(os.path.dirname(__file__), "..", "examples", "text-passthrough.json")


@pytest.fixture
def hello_llm_path():
    return os.path.join(os.path.dirname(__file__), "..", "examples", "hello-llm.json")


def test_load_workflow_from_file(text_passthrough_path):
    workflow = load_workflow_from_file(text_passthrough_path)
    assert len(workflow.nodes) == 2
    assert len(workflow.outputs) == 1
    assert workflow.outputs[0].name == "result"


def test_load_workflow_file_not_found():
    with pytest.raises(WorkflowFileNotFoundError):
        load_workflow_from_file("/nonexistent/path.json")


def test_load_workflow_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"nodes": "invalid"}')
        f.flush()
        try:
            with pytest.raises(WorkflowDeserializationError):
                load_workflow_from_file(f.name)
        finally:
            os.unlink(f.name)


def test_validate_hello_llm(hello_llm_path):
    workflow = load_workflow_from_file(hello_llm_path)
    assert len(workflow.nodes) == 1
    assert workflow.nodes[0].type == "LLM"
    assert len(workflow.inputs) == 1
    assert workflow.inputs[0].name == "prompt"


async def test_run_text_passthrough(text_passthrough_path):
    result = await run_workflow_from_file(text_passthrough_path)
    assert result["success"] is True
    assert result["output"]["result"] == "Hello from AceTeam!"


async def test_run_with_missing_file():
    with pytest.raises(WorkflowFileNotFoundError):
        await run_workflow_from_file("/nonexistent/path.json")
