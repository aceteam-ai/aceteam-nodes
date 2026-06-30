"""Tests for TelegramSendMessageNode.

The token is resolved through ``context.get_env`` and the Bot API call is
mocked, so these exercise the node's logic without network access or secrets.
"""

import pytest
from telegram.error import BadRequest
from workflow_engine import StringValue, WorkflowEngine, WorkflowException
from workflow_engine.contexts import InMemoryExecutionContext

from aceteam_nodes.nodes.telegram_send import (
    TelegramSendMessageInput,
    TelegramSendMessageNode,
)


def _node(engine: WorkflowEngine) -> TelegramSendMessageNode:
    return engine.create_node(TelegramSendMessageNode, id="test")


def _input(chat_id: str = "12345", text: str = "hello") -> TelegramSendMessageInput:
    return TelegramSendMessageInput(chat_id=StringValue(chat_id), text=StringValue(text))


class _FakeMessage:
    message_id = 99


def _mock_bot(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Patch Bot to capture send_message calls without network access."""
    captured: dict = {}

    class FakeBot:
        def __init__(self, token: str):
            self.token = token

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def send_message(self, chat_id, text, **kwargs):
            captured["token"] = self.token
            captured["chat_id"] = chat_id
            captured["text"] = text
            captured["kwargs"] = kwargs
            if "error" in captured:
                raise captured["error"]
            return _FakeMessage()

    monkeypatch.setattr("aceteam_nodes.nodes.telegram_send.Bot", FakeBot)
    return captured


@pytest.mark.asyncio
async def test_sends_message_and_maps_output(
    engine: WorkflowEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = _mock_bot(monkeypatch)

    output = await _node(engine).run(context=InMemoryExecutionContext(), input=_input())

    assert output.message_id.root == 99
    assert captured["token"] == "secret-token"
    assert captured["chat_id"] == "12345"
    assert captured["text"] == "hello"
    assert captured["kwargs"]["read_timeout"] == 30.0


@pytest.mark.asyncio
async def test_missing_token_raises(engine: WorkflowEngine, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(ValueError, match="Environment variable TELEGRAM_BOT_TOKEN is not set"):
        await _node(engine).run(context=InMemoryExecutionContext(), input=_input())


@pytest.mark.asyncio
async def test_api_error_raises_workflow_exception(
    engine: WorkflowEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    captured = _mock_bot(monkeypatch)
    captured["error"] = BadRequest("chat not found")

    with pytest.raises(WorkflowException, match="chat not found"):
        await _node(engine).run(context=InMemoryExecutionContext(), input=_input())
