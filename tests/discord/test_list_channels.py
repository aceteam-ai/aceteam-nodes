"""Tests for DiscordListChannelsNode."""

import pytest
from workflow_engine import (
    DataValue,
    ExecutionContext,
    IntegerValue,
    SequenceValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.discord.list_channels import (
    DiscordChannelItem,
    DiscordListChannelsNode,
)
from tests.discord.mocks import forbidden
from tests.workflow_helpers import error_messages, execute_single_node

_INPUT_FIELDS = {"guild_id": IntegerValue}
_OUTPUT_FIELDS = {"channels": SequenceValue[DataValue[DiscordChannelItem]]}


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

    result = await execute_single_node(
        engine,
        context,
        DiscordListChannelsNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"guild_id": IntegerValue(111)},
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

    result = await execute_single_node(
        engine,
        context,
        DiscordListChannelsNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"guild_id": IntegerValue(111)},
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
    captured["error"] = forbidden("Missing Access")

    result = await execute_single_node(
        engine,
        context,
        DiscordListChannelsNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"guild_id": IntegerValue(111)},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Missing Access" in message for message in error_messages(result))
