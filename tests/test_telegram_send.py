"""Tests for TelegramSendMessageNode.

The token is resolved through ``context.get_env`` and the Bot API call is
mocked, so these exercise the node's logic without network access or secrets.
"""

import httpx
import pytest
from workflow_engine import StringValue, WorkflowException
from workflow_engine.contexts.in_memory import InMemoryExecutionContext

from aceteam_nodes.nodes.telegram_send import (
    TelegramSendMessageInput,
    TelegramSendMessageNode,
    TelegramSendMessageParams,
)


def _node() -> TelegramSendMessageNode:
    return TelegramSendMessageNode(id="test", params=TelegramSendMessageParams())


def _input(chat_id: str = "12345", text: str = "hello") -> TelegramSendMessageInput:
    return TelegramSendMessageInput(chat_id=StringValue(chat_id), text=StringValue(text))


def _mock_post(monkeypatch: pytest.MonkeyPatch, status_code: int, body: dict) -> dict:
    """Patch httpx.AsyncClient.post to return a canned response; capture the call."""
    captured: dict = {}

    async def fake_post(self, url, *, json):
        captured["url"] = url
        captured["json"] = json
        return httpx.Response(
            status_code, json=body, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    return captured


@pytest.mark.asyncio
async def test_sends_message_and_maps_output(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = _mock_post(monkeypatch, 200, {"ok": True, "result": {"message_id": 99}})

    output = await _node().run(context=InMemoryExecutionContext(), input=_input())

    assert output.ok.root is True
    assert output.message_id.root == 99
    # token from get_env is in the URL, never in params; payload carries the args
    assert "bot secret-token".replace(" ", "") in captured["url"]
    assert captured["json"] == {"chat_id": "12345", "text": "hello"}


@pytest.mark.asyncio
async def test_missing_token_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(ValueError):
        await _node().run(context=InMemoryExecutionContext(), input=_input())


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    _mock_post(monkeypatch, 400, {"ok": False, "description": "chat not found"})

    with pytest.raises(WorkflowException, match="chat not found"):
        await _node().run(context=InMemoryExecutionContext(), input=_input())
