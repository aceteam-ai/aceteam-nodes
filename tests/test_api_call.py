"""Tests for APICallNode."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from workflow_engine import WorkflowEngine, WorkflowExecutionResultStatus
from workflow_engine.contexts import InMemoryExecutionContext

from aceteam_nodes.nodes.api_call import APICallNode


def _mock_httpx_client(*, capture: dict[str, str | None]) -> MagicMock:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"ok": True}

    async def request(**kwargs: object) -> MagicMock:
        capture["url"] = str(kwargs.get("url"))
        capture["method"] = str(kwargs.get("method"))
        return mock_response

    mock_client.request = request
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
async def test_execute_node_substitutes_input_into_url(engine: WorkflowEngine):
    """Runtime template values must come from input, not params.parameters."""
    context = InMemoryExecutionContext()
    capture: dict[str, str | None] = {"url": None, "method": None}
    params = {
        "url": "https://api.example.com/users/{{ employee_id }}",
        "method": "GET",
        "headers": {},
        "body_template": "",
        "parameters": {
            "employee_id": {
                "type": "string",
                "title": "employee_id",
                "description": "Employee id",
            },
        },
        "timeout": 30,
    }

    with patch(
        "aceteam_nodes.nodes.api_call.httpx.AsyncClient",
        return_value=_mock_httpx_client(capture=capture),
    ):
        result = await engine.execute_node(
            context=context,
            node=APICallNode,
            params=params,
            input={"employee_id": "42"},
        )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert capture["url"] == "https://api.example.com/users/42"
    assert capture["method"] == "GET"
    assert result.output is not None
    assert result.output["status_code"].root == 200
    assert result.output["response"].root == {"ok": True}


@pytest.mark.asyncio
async def test_execute_node_substitutes_input_into_body(engine: WorkflowEngine):
    context = InMemoryExecutionContext()
    capture: dict[str, object | None] = {"json": None, "method": None}
    params = {
        "url": "https://api.example.com/users",
        "method": "POST",
        "headers": {},
        "body_template": '{"employee_id": "{{ employee_id }}"}',
        "parameters": {
            "employee_id": {
                "type": "string",
                "title": "employee_id",
            },
        },
        "timeout": 30,
    }

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"created": True}

    async def request(**kwargs: object) -> MagicMock:
        capture["json"] = kwargs.get("json")
        capture["method"] = kwargs.get("method")
        return mock_response

    mock_client.request = request
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "aceteam_nodes.nodes.api_call.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await engine.execute_node(
            context=context,
            node=APICallNode,
            params=params,
            input={"employee_id": "42"},
        )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert capture["method"] == "POST"
    assert capture["json"] == {"employee_id": "42"}


@pytest.mark.asyncio
async def test_execute_node_substitutes_input_into_headers(engine: WorkflowEngine):
    context = InMemoryExecutionContext()
    capture: dict[str, object | None] = {"headers": None}
    params = {
        "url": "https://api.example.com/data",
        "method": "GET",
        "headers": {"Authorization": "Bearer {{ api_token }}"},
        "body_template": "",
        "parameters": {
            "api_token": {
                "type": "string",
                "title": "api_token",
            },
        },
        "timeout": 30,
    }

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"ok": True}

    async def request(**kwargs: object) -> MagicMock:
        capture["headers"] = kwargs.get("headers")
        return mock_response

    mock_client.request = request
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "aceteam_nodes.nodes.api_call.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await engine.execute_node(
            context=context,
            node=APICallNode,
            params=params,
            input={"api_token": "secret-abc"},
        )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert capture["headers"] == {"Authorization": "Bearer secret-abc"}


@pytest.mark.asyncio
async def test_undefined_template_variable_fails(engine: WorkflowEngine):
    """Undefined Jinja variables must fail loudly (StrictUndefined)."""
    context = InMemoryExecutionContext()
    params = {
        "url": "https://api.example.com/users/{{ employee_id }}",
        "method": "GET",
        "headers": {},
        "body_template": "",
        "parameters": {},
        "timeout": 30,
    }

    with patch("aceteam_nodes.nodes.api_call.httpx.AsyncClient"):
        result = await engine.execute_node(
            context=context,
            node=APICallNode,
            params=params,
            input={},
        )

    assert result.status is WorkflowExecutionResultStatus.ERROR
