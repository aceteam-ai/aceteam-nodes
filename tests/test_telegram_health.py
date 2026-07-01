"""Tests for TelegramHealthNode."""

import pytest
from telegram_mocks import FakeUser, bad_request, mock_bot
from workflow_engine import (
    BooleanValue,
    ExecutionContext,
    IntegerValue,
    StringValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)
from workflow_helpers import error_messages, execute_single_node

from aceteam_nodes.nodes.telegram.health import TelegramHealthNode

_OUTPUT_FIELDS = {
    "ok": BooleanValue,
    "bot_id": IntegerValue,
    "bot_username": StringValue,
}


@pytest.mark.asyncio
async def test_returns_bot_identity(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["bot_user"] = FakeUser(user_id=4242, username="aceteam-bot")

    result = await execute_single_node(
        engine,
        context,
        TelegramHealthNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["ok"].root is True
    assert result.output["bot_id"].root == 4242
    assert result.output["bot_username"].root == "aceteam-bot"
    assert "read_timeout" in captured["get_me"]


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
        TelegramHealthNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
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
    captured["error"] = bad_request("Unauthorized")

    result = await execute_single_node(
        engine,
        context,
        TelegramHealthNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Unauthorized" in message for message in error_messages(result))
