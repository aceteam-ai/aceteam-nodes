"""Tests for SlackSendMessageNode."""

import pytest
from slack_sdk.errors import SlackApiError
from workflow_engine import (
    ExecutionContext,
    StringValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)

from aceteam_nodes.nodes.slack_send import SlackSendMessageNode
from tests.workflow_helpers import error_messages, execute_single_node

_INPUT_FIELDS = {"channel": StringValue, "text": StringValue}
_OUTPUT_FIELDS = {"channel": StringValue, "timestamp": StringValue}


def _mock_client(monkeypatch: pytest.MonkeyPatch) -> dict:
    captured: dict = {}

    class FakeAsyncWebClient:
        def __init__(self, token: str | None = None, timeout: int = 30, **kwargs):
            captured["token"] = token
            captured["timeout"] = timeout

        async def chat_postMessage(self, *, channel: str, text: str, **kwargs):
            captured["channel"] = channel
            captured["text"] = text
            captured["kwargs"] = kwargs
            if "error" in captured:
                raise captured["error"]
            return captured.get(
                "response",
                {"ok": True, "channel": channel, "ts": "1700000000.000100"},
            )

    monkeypatch.setattr("aceteam_nodes.nodes.slack_send.AsyncWebClient", FakeAsyncWebClient)
    return captured


@pytest.mark.asyncio
async def test_posts_message_and_maps_output(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = _mock_client(monkeypatch)
    captured["response"] = {
        "ok": True,
        "channel": "C0123",
        "ts": "1700000000.000100",
    }

    result = await execute_single_node(
        engine,
        context,
        SlackSendMessageNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"channel": StringValue("C0123"), "text": StringValue("hello")},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["channel"].root == "C0123"
    assert result.output["timestamp"].root == "1700000000.000100"
    assert captured["token"] == "xoxb-secret"
    assert captured["timeout"] == 30
    assert captured["channel"] == "C0123"
    assert captured["text"] == "hello"


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
        SlackSendMessageNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"channel": StringValue("C0123"), "text": StringValue("hello")},
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
    captured = _mock_client(monkeypatch)
    captured["error"] = SlackApiError(
        "The request to the Slack API failed.",
        {"ok": False, "error": "channel_not_found"},
    )

    result = await execute_single_node(
        engine,
        context,
        SlackSendMessageNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"channel": StringValue("C0123"), "text": StringValue("hello")},
    )

    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("channel_not_found" in message for message in error_messages(result))


@pytest.mark.asyncio
async def test_resolves_channel_name_to_id(
    engine: WorkflowEngine,
    context: ExecutionContext,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = _mock_client(monkeypatch)
    captured["response"] = {
        "ok": True,
        "channel": "C0999RESOLVED",
        "ts": "1700000000.000200",
    }

    result = await execute_single_node(
        engine,
        context,
        SlackSendMessageNode,
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"channel": StringValue("#general"), "text": StringValue("hello")},
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert captured["channel"] == "#general"
    assert result.output["channel"].root == "C0999RESOLVED"
    assert result.output["timestamp"].root == "1700000000.000200"
