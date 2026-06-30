"""Tests for DiscordSendMessageNode.

The token is resolved through ``context.get_env`` and the REST call is mocked,
so these exercise the node's logic without network access or secrets.
"""

import discord
import pytest
from discord.errors import Forbidden
from workflow_engine import StringValue, WorkflowEngine, WorkflowException
from workflow_engine.contexts import InMemoryExecutionContext

from aceteam_nodes.nodes.discord_send import (
    DiscordSendMessageInput,
    DiscordSendMessageNode,
)


def _node(engine: WorkflowEngine) -> DiscordSendMessageNode:
    return engine.create_node(DiscordSendMessageNode, id="test")


def _input(channel_id: str = "987", content: str = "hello") -> DiscordSendMessageInput:
    return DiscordSendMessageInput(
        channel_id=StringValue(channel_id), content=StringValue(content)
    )


class _FakeMessage:
    id = 112233


def _forbidden(message: str) -> Forbidden:
    error = Forbidden.__new__(Forbidden)
    error.text = message
    error.status = 403
    assert error.text == message
    return error


def _mock_discord(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Patch discord.Client without network access."""
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

    monkeypatch.setattr("aceteam_nodes.nodes.discord_send.discord.Client", FakeClient)
    return captured


@pytest.mark.asyncio
async def test_sends_message_and_maps_output(
    engine: WorkflowEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_discord(monkeypatch)

    output = await _node(engine).run(context=InMemoryExecutionContext(), input=_input())

    assert output.message_id.root == 112233
    assert captured["token"] == "bot-secret"
    assert captured["channel_id"] == 987
    assert captured["content"] == "hello"
    assert captured["closed"] is True


@pytest.mark.asyncio
async def test_missing_token_raises(engine: WorkflowEngine, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    with pytest.raises(ValueError, match="Environment variable DISCORD_BOT_TOKEN is not set"):
        await _node(engine).run(context=InMemoryExecutionContext(), input=_input())


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_discord(monkeypatch)
    captured["error"] = _forbidden("Missing Access")

    with pytest.raises(WorkflowException, match="Missing Access"):
        await _node(engine).run(context=InMemoryExecutionContext(), input=_input())
