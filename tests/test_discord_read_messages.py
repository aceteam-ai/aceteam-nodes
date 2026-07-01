"""Tests for DiscordReadMessagesNode."""

from datetime import datetime, timezone

import discord
import pytest
from discord_mocks import forbidden
from workflow_engine import (
    DataValue,
    ExecutionContext,
    IntegerValue,
    NullValue,
    SequenceValue,
    UnionValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)
from workflow_helpers import error_messages, execute_single_node

from aceteam_nodes.nodes.discord.read_messages import (
    DiscordMessageItem,
    DiscordReadMessagesNode,
)

OptionalSnowflake = UnionValue[IntegerValue, NullValue]
_INPUT_FIELDS = {
    "channel_id": IntegerValue,
    "before": OptionalSnowflake,
    "after": OptionalSnowflake,
}
_OUTPUT_FIELDS = {"messages": SequenceValue[DataValue[DiscordMessageItem]]}


class _FakeAuthor:
    id = 555
    display_name = "tester"


class _FakeMessage:
    def __init__(self, message_id: int, content: str):
        self.id = message_id
        self.author = _FakeAuthor()
        self.content = content
        self.created_at = datetime(2026, 3, 1, tzinfo=timezone.utc)


def _mock_discord(monkeypatch: pytest.MonkeyPatch) -> dict:
    captured: dict = {}

    class FakeChannel(discord.abc.Messageable):
        async def history(self, *, limit=None, before=None, after=None, **kwargs):
            captured["history_kwargs"] = {
                "limit": limit,
                "before": before,
                "after": after,
            }
            if "error" in captured:
                raise captured["error"]
            for message_id, content in captured.get(
                "messages",
                [(111, "first"), (222, "second")],
            ):
                yield _FakeMessage(message_id, content)

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
async def test_reads_messages_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_discord(monkeypatch)

    result = await execute_single_node(
        engine,
        context,
        DiscordReadMessagesNode,
        input_fields={"channel_id": IntegerValue},
        output_fields=_OUTPUT_FIELDS,
        input={"channel_id": IntegerValue(987)},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    messages = result.output["messages"].root
    assert len(messages) == 2
    first = messages[0].root
    assert first.message_id.root == 111
    assert first.author_id.root == 555
    assert first.author_name.root == "tester"
    assert first.content.root == "first"
    assert first.created_at.root == "2026-03-01T00:00:00+00:00"
    assert captured["token"] == "bot-secret"
    assert captured["channel_id"] == 987
    assert captured["history_kwargs"]["limit"] is None
    assert captured["intents"].message_content is True


@pytest.mark.asyncio
async def test_passes_before_and_after_cursors(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_discord(monkeypatch)

    result = await execute_single_node(
        engine,
        context,
        DiscordReadMessagesNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={
            "channel_id": IntegerValue(987),
            "before": IntegerValue(1000),
            "after": IntegerValue(2000),
        },
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert captured["history_kwargs"]["before"].id == 1000
    assert captured["history_kwargs"]["after"].id == 2000


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
        DiscordReadMessagesNode,
        input_fields={"channel_id": IntegerValue},
        output_fields=_OUTPUT_FIELDS,
        input={"channel_id": IntegerValue(987)},
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
        DiscordReadMessagesNode,
        input_fields={"channel_id": IntegerValue},
        output_fields=_OUTPUT_FIELDS,
        input={"channel_id": IntegerValue(987)},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Missing Access" in message for message in error_messages(result))
