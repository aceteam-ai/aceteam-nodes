"""Telegram Send Message node - sends a message via the Telegram Bot API.

Mirrors the AceTeam ``telegram_send_message`` MCP tool as a self-contained
workflow node. The bot token is resolved from the execution environment via
``context.get_env`` (never baked into the workflow definition), so the only
platform coupling is whatever the context chooses to back ``get_env`` with.
"""

import logging
from typing import ClassVar, Literal, Type

import httpx
from overrides import override
from pydantic import Field
from workflow_engine import (
    BooleanValue,
    Data,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    Params,
    StringValue,
    WorkflowException,
)
from workflow_engine.core import StakeholderLevel

logger = logging.getLogger(__name__)

_TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramSendMessageParams(Params):
    bot_token_env: StringValue = Field(
        title="Bot Token Env Var",
        description=(
            "Name of the environment variable holding the Telegram bot token. "
            "The token itself is resolved at runtime, not stored in the workflow."
        ),
        default=StringValue("TELEGRAM_BOT_TOKEN"),
    )
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=IntegerValue(30),
    )


class TelegramSendMessageInput(Data):
    chat_id: StringValue = Field(
        title="Chat ID",
        description="Target chat: a numeric chat id or an @channelusername.",
    )
    text: StringValue = Field(
        title="Text",
        description="The message text to send.",
    )


class TelegramSendMessageOutput(Data):
    ok: BooleanValue = Field(
        title="OK",
        description="Whether Telegram accepted the message.",
    )
    message_id: IntegerValue = Field(
        title="Message ID",
        description="The id of the sent message.",
    )


class TelegramSendMessageNode(
    Node[
        TelegramSendMessageInput,
        TelegramSendMessageOutput,
        TelegramSendMessageParams,
    ]
):
    """Sends a message to a Telegram chat via the Bot API ``sendMessage`` method."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Telegram Send Message",
        description="Sends a message to a Telegram chat via the Bot API.",
        version="0.1.0",
        parameter_type=TelegramSendMessageParams,
    )

    type: Literal["TelegramSendMessage"] = "TelegramSendMessage"  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    @override
    def static_input_type(cls) -> Type[TelegramSendMessageInput]:
        return TelegramSendMessageInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[TelegramSendMessageOutput]:
        return TelegramSendMessageOutput

    @override
    async def run(
        self, context: ExecutionContext, input: TelegramSendMessageInput
    ) -> TelegramSendMessageOutput:
        token = await context.get_env(self.params.bot_token_env.root)
        url = f"{_TELEGRAM_API_BASE}/bot{token}/sendMessage"
        payload = {"chat_id": input.chat_id.root, "text": input.text.root}

        try:
            async with httpx.AsyncClient(timeout=self.params.timeout.root) as client:
                response = await client.post(url, json=payload)
        except httpx.RequestError as e:
            raise WorkflowException(
                f"Failed to reach Telegram: {e}",
                level=StakeholderLevel.USER,
            ) from e

        try:
            body = response.json()
        except ValueError as e:
            raise WorkflowException(
                "Telegram returned a non-JSON response.",
                level=StakeholderLevel.USER,
            ) from e

        if not response.is_success or not body.get("ok", False):
            description = body.get("description", f"HTTP {response.status_code}")
            raise WorkflowException(
                f"Telegram rejected the message: {description}",
                level=StakeholderLevel.USER,
            )

        result = body.get("result", {})
        return TelegramSendMessageOutput(
            ok=BooleanValue(True),
            message_id=IntegerValue(result.get("message_id", 0)),
        )


__all__ = [
    "TelegramSendMessageInput",
    "TelegramSendMessageNode",
    "TelegramSendMessageOutput",
    "TelegramSendMessageParams",
]
