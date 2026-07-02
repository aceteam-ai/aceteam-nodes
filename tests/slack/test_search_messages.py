"""Tests for SlackSearchMessagesNode."""

import pytest
from workflow_engine import (
    DataValue,
    ExecutionContext,
    SequenceValue,
    StringValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.slack.search_messages import (
    SlackSearchMatchItem,
    SlackSearchMessagesNode,
)
from tests.slack.mocks import mock_client, slack_api_error
from tests.workflow_helpers import error_messages, execute_single_node

_INPUT_FIELDS = {"query": StringValue}
_OUTPUT_FIELDS = {"matches": SequenceValue[DataValue[SlackSearchMatchItem]]}


@pytest.mark.asyncio
async def test_searches_messages_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_USER_TOKEN", "xoxp-secret")
    captured = mock_client(monkeypatch)

    result = await execute_single_node(
        engine,
        context,
        SlackSearchMessagesNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"query": StringValue("in:general hello")},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    match = result.output["matches"].root[0].root
    assert match.ts.root == "1700000000.000200"
    assert match.channel.root == "C0456"
    assert match.user.root == "U0789"
    assert match.text.root == "found it"
    assert "example.slack.com" in match.permalink.root
    assert captured["token"] == "xoxp-secret"
    assert captured["search_messages"]["query"] == "in:general hello"
    assert captured["search_messages"]["count"] == 20


@pytest.mark.asyncio
async def test_missing_user_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("SLACK_USER_TOKEN", raising=False)

    result = await execute_single_node(
        engine,
        context,
        SlackSearchMessagesNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"query": StringValue("hello")},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("SLACK_USER_TOKEN" in message for message in error_messages(result))


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_USER_TOKEN", "xoxp-secret")
    captured = mock_client(monkeypatch)
    captured["error"] = slack_api_error("missing_scope")

    result = await execute_single_node(
        engine,
        context,
        SlackSearchMessagesNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"query": StringValue("hello")},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("missing_scope" in message for message in error_messages(result))


@pytest.mark.asyncio
async def test_incomplete_match_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_USER_TOKEN", "xoxp-secret")
    captured = mock_client(monkeypatch)
    captured["search_response"] = {
        "ok": True,
        "messages": {"matches": [{"ts": "1700000000.000200"}]},
    }

    result = await execute_single_node(
        engine,
        context,
        SlackSearchMessagesNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"query": StringValue("hello")},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("channel id" in message for message in error_messages(result))
