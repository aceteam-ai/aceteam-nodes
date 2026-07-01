"""Tests for TelegramListChatsNode."""

import pytest
from telegram_mocks import FakeChat, bad_request, mock_bot
from workflow_engine import (
    ExecutionContext,
    StringValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)
from workflow_helpers import error_messages, execute_single_node

from aceteam_nodes.nodes.telegram.list_chats import TelegramListChatsNode

_INPUT_FIELDS = {"chat_id": StringValue}
_OUTPUT_FIELDS = {
    "chat_id": StringValue,
    "type": StringValue,
    "title": StringValue,
    "username": StringValue,
    "description": StringValue,
}


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

    result = await execute_single_node(
        engine,
        context,
        TelegramListChatsNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"chat_id": StringValue("@news")},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["chat_id"].root == "999"
    assert result.output["type"].root == "channel"
    assert result.output["title"].root == "Announcements"
    assert result.output["username"].root == "news"
    assert result.output["description"].root == "Official news"
    assert captured["get_chat"]["chat_id"] == "@news"


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
        TelegramListChatsNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"chat_id": StringValue("12345")},
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
    captured["error"] = bad_request("chat not found")

    result = await execute_single_node(
        engine,
        context,
        TelegramListChatsNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"chat_id": StringValue("12345")},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("chat not found" in message for message in error_messages(result))
