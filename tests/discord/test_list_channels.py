"""Tests for DiscordListChannelsNode."""

import pytest
from workflow_engine import (
    ExecutionContext,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.discord.list_channels import DiscordListChannelsNode
from tests.discord.mocks import forbidden


def _mock_discord(monkeypatch: pytest.MonkeyPatch) -> dict:
    captured: dict = {}

    class FakeChannel:
        def __init__(self, channel_id: int, name: str, type_name: str, position: int):
            self.id = channel_id
            self.name = name
            self.type = type(type_name, (), {"name": type_name})()
            self.position = position

    class FakeGuild:
        async def fetch_channels(self):
            if "error" in captured:
                raise captured["error"]
            return captured.get(
                "channels",
                [
                    FakeChannel(10, "general", "text", 0),
                    FakeChannel(20, "voice", "voice", 1),
                ],
            )

    class FakeClient:
        def __init__(self, *, intents, **kwargs):
            captured["intents"] = intents

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.close()

        async def login(self, token: str):
            captured["token"] = token

        async def fetch_guild(self, guild_id: int):
            captured["guild_id"] = guild_id
            return FakeGuild()

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr(
        "aceteam_nodes.nodes.discord.common.discord.Client",
        FakeClient,
    )
    return captured


@pytest.mark.asyncio
async def test_lists_channels_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_discord(monkeypatch)

    result = await engine.execute_node(
        context=context,
        node=DiscordListChannelsNode,
        input={"guild_id": 111},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    channels = result.output["channels"].root
    assert len(channels) == 2
    general = channels[0].root
    assert general.channel_id.root == 10
    assert general.name.root == "general"
    assert general.type.root == "text"
    assert general.position.root == 0
    assert captured["token"] == "bot-secret"
    assert captured["guild_id"] == 111


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)

    result = await engine.execute_node(
        context=context,
        node=DiscordListChannelsNode,
        input={"guild_id": 111},
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
        node=DiscordListChannelsNode,
        input={"guild_id": 111},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Missing Access" in message for message in result.errors.messages())
