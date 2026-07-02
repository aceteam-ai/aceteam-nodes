"""Tests for TelegramListChatsNode."""

import pytest
from workflow_engine import (
    ExecutionContext,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.telegram.list_chats import TelegramListChatsNode
from tests.telegram.mocks import FakeChat, bad_request, mock_bot


@pytest.mark.asyncio
async def test_looks_up_chat_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["chat"] = FakeChat(
        999,
        type="channel",
        title="Announcements",
        username="news",
        description="Official news",
    )

    result = await engine.execute_node(
        context=context,
        node=TelegramListChatsNode,
        input={"chat_id": "@news"},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["chat_id"].root == 999
    assert result.output["type"].root == "channel"
    assert result.output["title"].root == "Announcements"
    assert result.output["username"].root == "news"
    assert result.output["description"].root == "Official news"
    assert captured["get_chat"]["chat_id"] == "@news"


@pytest.mark.asyncio
async def test_nullable_fields_when_metadata_absent(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["chat"] = FakeChat(
        12345,
        type="private",
        title=None,
        username=None,
        description=None,
    )

    result = await engine.execute_node(
        context=context,
        node=TelegramListChatsNode,
        input={"chat_id": "12345"},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["chat_id"].root == 12345
    assert result.output["type"].root == "private"
    assert result.output["title"].root is None
    assert result.output["username"].root is None
    assert result.output["description"].root is None


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    result = await engine.execute_node(
        context=context,
        node=TelegramListChatsNode,
        input={"chat_id": "12345"},
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
    captured["error"] = bad_request("chat not found")

    result = await engine.execute_node(
        context=context,
        node=TelegramListChatsNode,
        input={"chat_id": "12345"},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("chat not found" in message for message in result.errors.messages())
