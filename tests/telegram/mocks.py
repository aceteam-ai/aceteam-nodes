"""Shared Telegram Bot API mocks for unit tests."""

from datetime import datetime, timezone

import pytest
from telegram.error import BadRequest


class FakeUser:
    def __init__(
        self,
        user_id: int = 555,
        username: str | None = "tester",
    ):
        self.id = user_id
        self.username = username


class FakeChat:
    def __init__(
        self,
        chat_id: int = 12345,
        *,
        type: str = "private",
        title: str | None = "Test Group",
        username: str | None = "testgroup",
        description: str | None = "A test chat",
    ):
        self.id = chat_id
        self.type = type
        self.title = title
        self.username = username
        self.description = description


class FakeMessage:
    def __init__(
        self,
        message_id: int = 99,
        *,
        chat_id: int = 12345,
        text: str | None = "hello",
        sender: FakeUser | None = None,
    ):
        self.message_id = message_id
        self.chat_id = chat_id
        self.text = text
        self.from_user = sender or FakeUser()
        self.date = datetime(2026, 3, 1, tzinfo=timezone.utc)


class FakeUpdate:
    def __init__(
        self,
        message: FakeMessage | None = None,
        *,
        update_id: int | None = None,
    ):
        self.message = message or FakeMessage()
        self.update_id = update_id if update_id is not None else self.message.message_id


class FakeSendMessage:
    message_id = 99


def mock_bot(monkeypatch: pytest.MonkeyPatch) -> dict:
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
            return FakeSendMessage()

        async def get_updates(self, *, offset=None, limit=None, timeout=None, **kwargs):
            call = {
                "offset": offset,
                "limit": limit,
                "timeout": timeout,
                **kwargs,
            }
            captured.setdefault("get_updates_calls", []).append(call)
            captured["get_updates"] = call
            if "error" in captured:
                raise captured["error"]
            batches = captured.get("update_batches")
            if batches is not None:
                call_index = len(captured["get_updates_calls"]) - 1
                if call_index < len(batches):
                    return batches[call_index]
                return ()
            return captured.get("updates", (FakeUpdate(),))

        async def get_chat(self, chat_id, **kwargs):
            captured["get_chat"] = {"chat_id": chat_id, **kwargs}
            if "error" in captured:
                raise captured["error"]
            return captured.get(
                "chat",
                FakeChat(
                    chat_id=int(chat_id) if str(chat_id).lstrip("-").isdigit() else 12345,
                    title="Test Group",
                    username="testgroup",
                    description="A test chat",
                    type="supergroup",
                ),
            )

        async def get_me(self, **kwargs):
            captured["get_me"] = kwargs
            if "error" in captured:
                raise captured["error"]
            return captured.get("bot_user", FakeUser(user_id=4242, username="aceteam-bot"))

    for target in (
        "aceteam_nodes.nodes.telegram.send.Bot",
        "aceteam_nodes.nodes.telegram.read_messages.Bot",
        "aceteam_nodes.nodes.telegram.list_chats.Bot",
        "aceteam_nodes.nodes.telegram.bot_info.Bot",
    ):
        monkeypatch.setattr(target, FakeBot)
    return captured


def bad_request(message: str) -> BadRequest:
    return BadRequest(message)
