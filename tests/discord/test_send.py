"""Tests for DiscordSendMessageNode."""

import discord
import pytest
from workflow_engine import (
    ExecutionContext,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.discord.send import DiscordSendMessageNode
from tests.discord.mocks import forbidden


class _FakeMessage:
    id = 112233


def _mock_discord(monkeypatch: pytest.MonkeyPatch) -> dict:
    captured: dict = {}

    class FakeChannel(discord.abc.Messageable):
        async def send(self, content: str | None = None, **kwargs):
            captured["content"] = content
            captured["kwargs"] = kwargs
            if "error" in captured:
                raise captured["error"]
            return _FakeMessage()

    class FakeClient:
        def __init__(self, *, intents, **kwargs):
            captured["intents"] = intents

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.close()

        async def login(self, token: str):
            captured["token"] = token

        async def fetch_channel(self, channel_id: int):
            captured["channel_id"] = channel_id
            return FakeChannel()

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr(
        "aceteam_nodes.nodes.discord.common.discord.Client",
        FakeClient,
    )
    return captured


@pytest.mark.asyncio
async def test_sends_message_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_discord(monkeypatch)

    result = await engine.execute_node(
        context=context,
        node=DiscordSendMessageNode,
        input={"channel_id": 987, "content": "hello"},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["message_id"].root == 112233
    assert captured["token"] == "bot-secret"
    assert captured["channel_id"] == 987
    assert captured["content"] == "hello"
    assert captured["closed"] is True


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)

    result = await engine.execute_node(
        context=context,
        node=DiscordSendMessageNode,
        input={"channel_id": 987, "content": "hello"},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("DISCORD_BOT_TOKEN" in message for message in result.errors.messages())


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_discord(monkeypatch)
    captured["error"] = forbidden("Missing Access")

    result = await engine.execute_node(
        context=context,
        node=DiscordSendMessageNode,
        input={"channel_id": 987, "content": "hello"},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Missing Access" in message for message in result.errors.messages())
