"""Tests for TelegramBotInfoNode."""

import pytest
from workflow_engine import (
    ExecutionContext,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.telegram.bot_info import TelegramBotInfoNode
from tests.telegram.mocks import FakeUser, bad_request, mock_bot


@pytest.mark.asyncio
async def test_returns_bot_identity(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["bot_user"] = FakeUser(user_id=4242, username="aceteam-bot")

    result = await engine.execute_node(
        context=context,
        node=TelegramBotInfoNode,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["bot_id"].root == 4242
    assert result.output["bot_username"].root == "aceteam-bot"
    assert "read_timeout" in captured["get_me"]


@pytest.mark.asyncio
async def test_nullable_username_when_unset(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = mock_bot(monkeypatch)
    captured["bot_user"] = FakeUser(user_id=4242, username=None)

    result = await engine.execute_node(
        context=context,
        node=TelegramBotInfoNode,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["bot_id"].root == 4242
    assert result.output["bot_username"].root is None


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    result = await engine.execute_node(
        context=context,
        node=TelegramBotInfoNode,
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
    captured["error"] = bad_request("Unauthorized")

    result = await engine.execute_node(
        context=context,
        node=TelegramBotInfoNode,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Unauthorized" in message for message in result.errors.messages())
