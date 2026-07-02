"""Tests for SlackReadMessagesNode."""

import pytest
from workflow_engine import (
    DataValue,
    ExecutionContext,
    NullValue,
    SequenceValue,
    StringValue,
    UnionValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.slack.read_messages import (
    SlackMessageItem,
    SlackReadMessagesNode,
)
from tests.slack.mocks import mock_client, slack_api_error
from tests.workflow_helpers import error_messages, execute_single_node

OptionalString = UnionValue[StringValue, NullValue]
_INPUT_FIELDS = {
    "channel_id": StringValue,
    "oldest": OptionalString,
    "latest": OptionalString,
}
_OUTPUT_FIELDS = {"messages": SequenceValue[DataValue[SlackMessageItem]]}


@pytest.mark.asyncio
async def test_reads_messages_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = mock_client(monkeypatch)
    captured["history_response"] = {
        "ok": True,
        "messages": [
            {
                "ts": "1700000000.000100",
                "user": "U0123",
                "text": "hello",
                "thread_ts": "1700000000.000050",
            }
        ],
    }

    result = await execute_single_node(
        engine,
        context,
        SlackReadMessagesNode,
        input_fields={"channel_id": StringValue},
        output_fields=_OUTPUT_FIELDS,
        input={"channel_id": StringValue("C0123")},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    message = result.output["messages"].root[0].root
    assert message.ts.root == "1700000000.000100"
    assert message.user.root == "U0123"
    assert message.text.root == "hello"
    assert message.thread_ts.root == "1700000000.000050"
    assert captured["conversations_history"]["channel"] == "C0123"
    assert captured["conversations_history"]["limit"] == 200


@pytest.mark.asyncio
async def test_paginates_history(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = mock_client(monkeypatch)
    captured["history_batches"] = (
        {
            "ok": True,
            "messages": [{"ts": "1.000001", "user": "U1", "text": "first"}],
            "response_metadata": {"next_cursor": "cursor-1"},
        },
        {
            "ok": True,
            "messages": [{"ts": "2.000001", "user": "U2", "text": "second"}],
        },
    )

    result = await execute_single_node(
        engine,
        context,
        SlackReadMessagesNode,
        input_fields={"channel_id": StringValue},
        output_fields=_OUTPUT_FIELDS,
        input={"channel_id": StringValue("C0123")},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert len(result.output["messages"].root) == 2
    calls = captured["conversations_history_calls"]
    assert len(calls) == 2
    assert calls[1]["cursor"] == "cursor-1"


@pytest.mark.asyncio
async def test_passes_oldest_and_latest(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = mock_client(monkeypatch)

    result = await execute_single_node(
        engine,
        context,
        SlackReadMessagesNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={
            "channel_id": StringValue("C0123"),
            "oldest": StringValue("100.000000"),
            "latest": StringValue("200.000000"),
        },
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert captured["conversations_history"]["oldest"] == "100.000000"
    assert captured["conversations_history"]["latest"] == "200.000000"


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

    result = await execute_single_node(
        engine,
        context,
        SlackReadMessagesNode,
        input_fields={"channel_id": StringValue},
        output_fields=_OUTPUT_FIELDS,
        input={"channel_id": StringValue("C0123")},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("SLACK_BOT_TOKEN" in message for message in error_messages(result))


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = mock_client(monkeypatch)
    captured["error"] = slack_api_error("not_in_channel")

    result = await execute_single_node(
        engine,
        context,
        SlackReadMessagesNode,
        input_fields={"channel_id": StringValue},
        output_fields=_OUTPUT_FIELDS,
        input={"channel_id": StringValue("C0123")},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("not_in_channel" in message for message in error_messages(result))
