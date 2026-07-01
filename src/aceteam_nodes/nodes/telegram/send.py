"""Telegram Send Message node - sends a message via the Telegram Bot API."""

import logging
from typing import ClassVar, Type

from overrides import override
from pydantic import Field
from telegram import Bot
from telegram.error import TelegramError
from workflow_engine import (
    Data,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    Params,
    StringValue,
)

from .common import TELEGRAM_TOKEN_ENV_VAR, raise_telegram_api_error

logger = logging.getLogger(__name__)


class TelegramSendMessageParams(Params):
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
        self,
        *,
        context: ExecutionContext,
        input_type: Type[TelegramSendMessageInput],
        output_type: Type[TelegramSendMessageOutput],
        input: TelegramSendMessageInput,
    ) -> TelegramSendMessageOutput:
        token = await context.get_env(TELEGRAM_TOKEN_ENV_VAR)
        timeout = float(self.params.timeout.root)

        try:
            async with Bot(token=token) as bot:
                message = await bot.send_message(
                    chat_id=input.chat_id.root,
                    text=input.text.root,
                    read_timeout=timeout,
                    write_timeout=timeout,
                    connect_timeout=timeout,
                )
        except TelegramError as e:
            raise_telegram_api_error(e)

        return output_type(
            message_id=IntegerValue(message.message_id),
        )


__all__ = (
    "TelegramSendMessageInput",
    "TelegramSendMessageNode",
    "TelegramSendMessageOutput",
    "TelegramSendMessageParams",
)
