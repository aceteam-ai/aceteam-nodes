"""Tests for TelegramReadMessagesNode."""

import pytest
from telegram_mocks import FakeMessage, FakeUpdate, FakeUser, bad_request, mock_bot
from workflow_engine import (
    DataValue,
    ExecutionContext,
    IntegerValue,
    NullValue,
    SequenceValue,
    UnionValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)
from workflow_helpers import error_messages, execute_single_node

from aceteam_nodes.nodes.telegram.read_messages import (
    TelegramMessageItem,
    TelegramReadMessagesNode,
)

OptionalOffset = UnionValue[IntegerValue, NullValue]
_OUTPUT_FIELDS = {"messages": SequenceValue[DataValue[TelegramMessageItem]]}


@pytest.mark.asyncio
async def test_reads_messages_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["updates"] = (
        FakeUpdate(FakeMessage(99, text="hello")),
        FakeUpdate(FakeMessage(100, text="world", sender=FakeUser(777, "alice"))),
    )

    result = await execute_single_node(
        engine,
        context,
        TelegramReadMessagesNode,
        input_fields={"limit": IntegerValue},
        output_fields=_OUTPUT_FIELDS,
        input={"limit": IntegerValue(100)},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    messages = result.output["messages"].root
    assert len(messages) == 2
    first = messages[0].root
    assert first.message_id.root == 99
    assert first.chat_id.root == "12345"
    assert first.sender_id.root == 555
    assert first.sender_username.root == "tester"
    assert first.text.root == "hello"
    assert first.date.root == "2026-03-01T00:00:00+00:00"
    assert captured["get_updates"]["limit"] == 100
    assert captured["get_updates"]["offset"] is None


@pytest.mark.asyncio
async def test_passes_offset(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)

    result = await execute_single_node(
        engine,
        context,
        TelegramReadMessagesNode,
        input_fields={"offset": OptionalOffset, "limit": IntegerValue},
        output_fields=_OUTPUT_FIELDS,
        input={"offset": IntegerValue(42), "limit": IntegerValue(10)},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert captured["get_updates"]["offset"] == 42
    assert captured["get_updates"]["limit"] == 10


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    result = await execute_single_node(
        engine,
        context,
        TelegramReadMessagesNode,
        input_fields={"limit": IntegerValue},
        output_fields=_OUTPUT_FIELDS,
        input={"limit": IntegerValue(100)},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("TELEGRAM_BOT_TOKEN" in message for message in error_messages(result))


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["error"] = bad_request("Conflict")

    result = await execute_single_node(
        engine,
        context,
        TelegramReadMessagesNode,
        input_fields={"limit": IntegerValue},
        output_fields=_OUTPUT_FIELDS,
        input={"limit": IntegerValue(100)},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Conflict" in message for message in error_messages(result))
