"""Tests for TelegramReadMessagesNode."""

from datetime import datetime, timezone

import pytest
from workflow_engine import (
    ExecutionContext,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.telegram.read_messages import TelegramReadMessagesNode
from tests.telegram.mocks import FakeMessage, FakeUpdate, FakeUser, bad_request, mock_bot


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

    result = await engine.execute_node(
        context=context,
        node=TelegramReadMessagesNode,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    messages = result.output["messages"].root
    assert len(messages) == 2
    first = messages[0].root
    assert first.message_id.root == 99
    assert first.chat_id.root == 12345
    assert first.sender_id.root == 555
    assert first.sender_username.root == "tester"
    assert first.text.root == "hello"
    assert first.date.root == datetime(2026, 3, 1, tzinfo=timezone.utc)
    assert captured["get_updates"]["limit"] == 100
    assert captured["get_updates"]["offset"] is None


@pytest.mark.asyncio
async def test_nullable_fields_for_missing_text_and_username(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["updates"] = (
        FakeUpdate(FakeMessage(99, text=None, sender=FakeUser(555, username=None))),
    )

    result = await engine.execute_node(
        context=context,
        node=TelegramReadMessagesNode,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    item = result.output["messages"].root[0].root
    assert item.sender_id.root == 555
    assert item.sender_username.root is None
    assert item.text.root is None


@pytest.mark.asyncio
async def test_passes_offset(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)

    result = await engine.execute_node(
        context=context,
        node=TelegramReadMessagesNode,
        input={"offset": 42},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert captured["get_updates"]["offset"] == 42
    assert captured["get_updates"]["limit"] == 100


@pytest.mark.asyncio
async def test_paginates_until_queue_is_exhausted(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["update_batches"] = (
        tuple(
            FakeUpdate(FakeMessage(update_id), update_id=update_id) for update_id in range(1, 101)
        ),
        tuple(
            FakeUpdate(FakeMessage(update_id), update_id=update_id) for update_id in range(101, 151)
        ),
    )

    result = await engine.execute_node(
        context=context,
        node=TelegramReadMessagesNode,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert len(result.output["messages"].root) == 150
    calls = captured["get_updates_calls"]
    assert len(calls) == 2
    assert calls[0]["offset"] is None
    assert calls[0]["limit"] == 100
    assert calls[0]["timeout"] == 30
    assert calls[1]["offset"] == 101
    assert calls[1]["limit"] == 100
    assert calls[1]["timeout"] == 0


@pytest.mark.asyncio
async def test_zero_poll_timeout_when_timeout_below_one(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)

    result = await engine.execute_node(
        context=context,
        node=TelegramReadMessagesNode,
        params={"timeout": 0},
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert captured["get_updates"]["timeout"] == 0


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    result = await engine.execute_node(
        context=context,
        node=TelegramReadMessagesNode,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("TELEGRAM_BOT_TOKEN" in message for message in result.errors.messages())


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["error"] = bad_request("Conflict")

    result = await engine.execute_node(
        context=context,
        node=TelegramReadMessagesNode,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Conflict" in message for message in result.errors.messages())
