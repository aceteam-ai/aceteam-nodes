"""Tests for DiscordSendMessageNode.

The token is resolved through ``context.get_env`` and the REST call is mocked,
so these exercise the node's logic without network access or secrets.
"""

import httpx
import pytest
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
async def test_sends_message_and_maps_output(
    engine: WorkflowEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-secret")
    captured = _mock_post(monkeypatch, 200, {"id": "112233", "content": "hello"})

    output = await _node(engine).run(context=InMemoryExecutionContext(), input=_input())

    assert output.message_id.root == "112233"
    assert captured["headers"]["Authorization"] == "Bot bot-secret"
    assert captured["url"].endswith("/channels/987/messages")
    assert captured["json"] == {"content": "hello"}


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
    _mock_post(monkeypatch, 403, {"message": "Missing Access", "code": 50001})

    with pytest.raises(WorkflowException, match="Missing Access"):
        await _node(engine).run(context=InMemoryExecutionContext(), input=_input())
