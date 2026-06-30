"""Tests for SlackSendMessageNode.

The token is resolved through ``context.get_env`` and the Web API call is
mocked, so these exercise the node's logic without network access or secrets.
"""

import pytest
from slack_sdk.errors import SlackApiError
from workflow_engine import StringValue, WorkflowEngine, WorkflowException
from workflow_engine.contexts import InMemoryExecutionContext

from aceteam_nodes.nodes.slack_send import (
    SlackSendMessageInput,
    SlackSendMessageNode,
)


def _node(engine: WorkflowEngine) -> SlackSendMessageNode:
    return engine.create_node(SlackSendMessageNode, id="test")


def _input(channel: str = "C0123", text: str = "hello") -> SlackSendMessageInput:
    return SlackSendMessageInput(channel=StringValue(channel), text=StringValue(text))


def _mock_client(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Patch AsyncWebClient to capture chat_postMessage calls without network access."""
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
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = _mock_client(monkeypatch)
    captured["response"] = {
        "ok": True,
        "channel": "C0123",
        "ts": "1700000000.000100",
    }

    output = await _node(engine).run(context=InMemoryExecutionContext(), input=_input())

    assert output.ok.root is True
    assert output.channel.root == "C0123"
    assert output.ts.root == "1700000000.000100"
    assert captured["token"] == "xoxb-secret"
    assert captured["timeout"] == 30
    assert captured["channel"] == "C0123"
    assert captured["text"] == "hello"


@pytest.mark.asyncio
async def test_missing_token_raises(engine: WorkflowEngine, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    with pytest.raises(ValueError, match="Environment variable SLACK_BOT_TOKEN is not set"):
        await _node(engine).run(context=InMemoryExecutionContext(), input=_input())


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = _mock_client(monkeypatch)
    captured["error"] = SlackApiError(
        "The request to the Slack API failed.",
        {"ok": False, "error": "channel_not_found"},
    )

    with pytest.raises(WorkflowException, match="channel_not_found"):
        await _node(engine).run(context=InMemoryExecutionContext(), input=_input())
