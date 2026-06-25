"""Tests for SlackSendMessageNode.

The token is resolved through ``context.get_env`` and the Web API call is
mocked, so these exercise the node's logic without network access or secrets.
"""

import httpx
import pytest
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


def _mock_post(monkeypatch: pytest.MonkeyPatch, status_code: int, body: dict) -> dict:
    """Patch httpx.AsyncClient.post to return a canned response; capture the call."""
    captured: dict = {}

    async def fake_post(self, url, *, headers, json):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return httpx.Response(
            status_code, json=body, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    return captured


@pytest.mark.asyncio
async def test_posts_message_and_maps_output(
    engine: WorkflowEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-secret")
    captured = _mock_post(
        monkeypatch, 200, {"ok": True, "channel": "C0123", "ts": "1700000000.000100"}
    )

    output = await _node(engine).run(context=InMemoryExecutionContext(), input=_input())

    assert output.ok.root is True
    assert output.channel.root == "C0123"
    assert output.ts.root == "1700000000.000100"
    # token from get_env goes in the Authorization header, never in params
    assert captured["headers"]["Authorization"] == "Bearer xoxb-secret"
    assert captured["json"] == {"channel": "C0123", "text": "hello"}


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
    # Slack reports app-level failures as ok=false with a 200 status.
    _mock_post(monkeypatch, 200, {"ok": False, "error": "channel_not_found"})

    with pytest.raises(WorkflowException, match="channel_not_found"):
        await _node(engine).run(context=InMemoryExecutionContext(), input=_input())
