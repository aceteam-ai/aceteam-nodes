"""Tests for SlackListChannelsNode."""

import pytest
from workflow_engine import (
    DataValue,
    ExecutionContext,
    NullValue,
    SequenceValue,
    StringValue,
    UnionValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.slack.list_channels import (
    SlackChannelItem,
    SlackListChannelsNode,
)
from tests.slack.mocks import mock_client, slack_api_error
from tests.workflow_helpers import error_messages, execute_single_node

OptionalString = UnionValue[StringValue, NullValue]
_OUTPUT_FIELDS = {"channels": SequenceValue[DataValue[SlackChannelItem]]}


@pytest.mark.asyncio
async def test_lists_channels_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = mock_client(monkeypatch)

    result = await execute_single_node(
        engine,
        context,
        SlackListChannelsNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    channel = result.output["channels"].root[0].root
    assert channel.channel_id.root == "C0123"
    assert channel.name.root == "general"
    assert channel.is_private.root is False
    assert channel.num_members.root == 42
    assert captured["conversations_list"]["types"] == "public_channel,private_channel"
    assert captured["conversations_list"]["limit"] == 200


@pytest.mark.asyncio
async def test_paginates_channel_list(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = mock_client(monkeypatch)
    captured["list_batches"] = (
        {
            "ok": True,
            "channels": [{"id": "C1", "name": "one", "is_private": False, "num_members": 1}],
            "response_metadata": {"next_cursor": "cursor-1"},
        },
        {
            "ok": True,
            "channels": [{"id": "C2", "name": "two", "is_private": True, "num_members": 2}],
        },
    )

    result = await execute_single_node(
        engine,
        context,
        SlackListChannelsNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert len(result.output["channels"].root) == 2
    calls = captured["conversations_list_calls"]
    assert len(calls) == 2
    assert calls[1]["cursor"] == "cursor-1"


@pytest.mark.asyncio
async def test_missing_token_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)

    result = await execute_single_node(
        engine,
        context,
        SlackListChannelsNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("SLACK_BOT_TOKEN" in message for message in error_messages(result))


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = mock_client(monkeypatch)
    captured["error"] = slack_api_error("missing_scope")

    result = await execute_single_node(
        engine,
        context,
        SlackListChannelsNode,
        input_fields={},
        output_fields=_OUTPUT_FIELDS,
        input={},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("missing_scope" in message for message in error_messages(result))
