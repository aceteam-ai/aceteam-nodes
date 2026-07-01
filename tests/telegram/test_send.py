"""Tests for TelegramSendMessageNode."""

import pytest
from telegram.error import BadRequest
from workflow_engine import (
    ExecutionContext,
    IntegerValue,
    StringValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.telegram.send import TelegramSendMessageNode
from tests.telegram.mocks import mock_bot
from tests.workflow_helpers import error_messages, execute_single_node

_INPUT_FIELDS = {"chat_id": StringValue, "text": StringValue}
_OUTPUT_FIELDS = {"message_id": IntegerValue}


@pytest.mark.asyncio
async def test_sends_message_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)

    result = await execute_single_node(
        engine,
        context,
        TelegramSendMessageNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"chat_id": StringValue("12345"), "text": StringValue("hello")},
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

    result = await execute_single_node(
        engine,
        context,
        TelegramSendMessageNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"chat_id": StringValue("12345"), "text": StringValue("hello")},
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
    captured["error"] = BadRequest("chat not found")

    result = await execute_single_node(
        engine,
        context,
        TelegramSendMessageNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"chat_id": StringValue("12345"), "text": StringValue("hello")},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("chat not found" in message for message in error_messages(result))
