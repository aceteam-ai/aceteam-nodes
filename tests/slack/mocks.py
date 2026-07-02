"""Shared Slack Web API mocks for unit tests."""

import pytest
from slack_sdk.errors import SlackApiError


def slack_api_error(error_code: str) -> SlackApiError:
    return SlackApiError(
        "The request to the Slack API failed.",
        {"ok": False, "error": error_code},
    )


def mock_client(monkeypatch: pytest.MonkeyPatch) -> dict:
    captured: dict = {}

    class FakeAsyncWebClient:
        def __init__(self, token: str | None = None, timeout: int = 30, **kwargs):
            captured["token"] = token
            captured["timeout"] = timeout

        async def chat_postMessage(self, *, channel: str, text: str, **kwargs):
            captured["chat_postMessage"] = {"channel": channel, "text": text, **kwargs}
            if "error" in captured:
                raise captured["error"]
            return captured.get(
                "chat_postMessage_response",
                {"ok": True, "channel": channel, "ts": "1700000000.000100"},
            )

        async def conversations_history(self, **kwargs):
            captured.setdefault("conversations_history_calls", []).append(kwargs)
            captured["conversations_history"] = kwargs
            if "error" in captured:
                raise captured["error"]
            batches = captured.get("history_batches")
            if batches is not None:
                call_index = len(captured["conversations_history_calls"]) - 1
                if call_index < len(batches):
                    return batches[call_index]
                return {"ok": True, "messages": []}
            return captured.get(
                "history_response",
                {
                    "ok": True,
                    "messages": [
                        {
                            "ts": "1700000000.000100",
                            "user": "U0123",
                            "text": "hello",
                        }
                    ],
                },
            )

        async def search_messages(self, *, query: str, count: int, **kwargs):
            captured["search_messages"] = {"query": query, "count": count, **kwargs}
            if "error" in captured:
                raise captured["error"]
            return captured.get(
                "search_response",
                {
                    "ok": True,
                    "messages": {
                        "matches": [
                            {
                                "ts": "1700000000.000200",
                                "channel": {"id": "C0456"},
                                "user": "U0789",
                                "text": "found it",
                                "permalink": "https://example.slack.com/archives/C0456/p1700000000000200",
                            }
                        ]
                    },
                },
            )

        async def conversations_list(self, **kwargs):
            captured.setdefault("conversations_list_calls", []).append(kwargs)
            captured["conversations_list"] = kwargs
            if "error" in captured:
                raise captured["error"]
            batches = captured.get("list_batches")
            if batches is not None:
                call_index = len(captured["conversations_list_calls"]) - 1
                if call_index < len(batches):
                    return batches[call_index]
                return {"ok": True, "channels": []}
            return captured.get(
                "list_response",
                {
                    "ok": True,
                    "channels": [
                        {
                            "id": "C0123",
                            "name": "general",
                            "is_private": False,
                            "num_members": 42,
                        }
                    ],
                },
            )

    for target in (
        "aceteam_nodes.nodes.slack.send.AsyncWebClient",
        "aceteam_nodes.nodes.slack.read_messages.AsyncWebClient",
        "aceteam_nodes.nodes.slack.search_messages.AsyncWebClient",
        "aceteam_nodes.nodes.slack.list_channels.AsyncWebClient",
    ):
        monkeypatch.setattr(target, FakeAsyncWebClient)
    return captured
