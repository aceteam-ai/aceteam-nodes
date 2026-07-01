"""Tests for DiscordBotInfoNode."""

import pytest
from workflow_engine import (
    ExecutionContext,
    IntegerValue,
    StringValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.discord.bot_info import DiscordBotInfoNode
from tests.discord.mocks import forbidden
from tests.workflow_helpers import error_messages, execute_single_node

_OUTPUT_FIELDS = {"bot_id": IntegerValue, "bot_username": StringValue}


def _mock_discord(monkeypatch: pytest.MonkeyPatch) -> dict:
    captured: dict = {}

    class FakeUser:
        id = 4242
        name = "aceteam-bot"

    class FakeClient:
        def __init__(self, *, intents, **kwargs):
            captured["intents"] = intents
            self.user = FakeUser()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.close()

        async def login(self, token: str):
            captured["token"] = token
            if "error" in captured:
                raise captured["error"]

        async def application_info(self):
            if "app_error" in captured:
                raise captured["app_error"]

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr(
        "aceteam_nodes.nodes.discord.common.discord.Client",
        FakeClient,
    )
    return captured


@pytest.mark.asyncio
async def test_returns_bot_identity(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_discord(monkeypatch)

    result = await execute_single_node(
        engine,
        context,
        DiscordBotInfoNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["bot_id"].root == 4242
    assert result.output["bot_username"].root == "aceteam-bot"
    assert captured["token"] == "bot-secret"


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)

    result = await execute_single_node(
        engine,
        context,
        DiscordBotInfoNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("DISCORD_BOT_TOKEN" in message for message in error_messages(result))


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_discord(monkeypatch)
    captured["error"] = forbidden("Improper token")

    result = await execute_single_node(
        engine,
        context,
        DiscordBotInfoNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Improper token" in message for message in error_messages(result))
