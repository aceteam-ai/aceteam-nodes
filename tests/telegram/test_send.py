"""Tests for TelegramSendMessageNode."""

import pytest
from telegram.error import BadRequest
from workflow_engine import (
    ExecutionContext,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.telegram.send import TelegramSendMessageNode
from tests.telegram.mocks import mock_bot


@pytest.mark.asyncio
async def test_sends_message_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)

    result = await engine.execute_node(
        context=context,
        node=TelegramSendMessageNode,
        input={"chat_id": "12345", "text": "hello"},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["message_id"].root == 99
    assert captured["token"] == "secret-token"
    assert captured["chat_id"] == "12345"
    assert captured["text"] == "hello"
    assert captured["kwargs"]["read_timeout"] == 30.0


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    result = await engine.execute_node(
        context=context,
        node=TelegramSendMessageNode,
        input={"chat_id": "12345", "text": "hello"},
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
    captured["error"] = BadRequest("chat not found")

    result = await engine.execute_node(
        context=context,
        node=TelegramSendMessageNode,
        input={"chat_id": "12345", "text": "hello"},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("chat not found" in message for message in result.errors.messages())
