"""Telegram Health node - verifies the bot token via ``getMe``."""

from typing import ClassVar, Type

from overrides import override
from pydantic import Field
from telegram import Bot
from telegram.error import TelegramError
from workflow_engine import (
    BooleanValue,
    Data,
    Empty,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    Params,
    StringValue,
)

from .common import TELEGRAM_TOKEN_ENV_VAR, raise_telegram_api_error


class TelegramHealthParams(Params):
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=IntegerValue(30),
    )


class TelegramHealthOutput(Data):
    ok: BooleanValue = Field(
        title="OK",
        description="Whether the token was accepted by ``getMe``.",
    )
    bot_id: IntegerValue = Field(
        title="Bot ID",
        description="The bot's Telegram user id.",
    )
    bot_username: StringValue = Field(
        title="Bot Username",
        description="The bot's @username, if set.",
    )


class TelegramHealthNode(
    Node[
        Empty,
        TelegramHealthOutput,
        TelegramHealthParams,
    ]
):
    """Verify ``TELEGRAM_BOT_TOKEN`` via the Bot API ``getMe`` method."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Telegram Health",
        description="Verifies the configured bot token via ``getMe``.",
        version="0.1.0",
        parameter_type=TelegramHealthParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[Empty]:
        return Empty

    @classmethod
    @override
    def static_output_type(cls) -> Type[TelegramHealthOutput]:
        return TelegramHealthOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[Empty],
        output_type: Type[TelegramHealthOutput],
        input: Empty,
    ) -> TelegramHealthOutput:
        token = await context.get_env(TELEGRAM_TOKEN_ENV_VAR)
        timeout = float(self.params.timeout.root)

        try:
            async with Bot(token=token) as bot:
                bot_user = await bot.get_me(
                    read_timeout=timeout,
                    write_timeout=timeout,
                    connect_timeout=timeout,
                )
        except TelegramError as e:
            raise_telegram_api_error(e)

        return output_type(
            ok=BooleanValue(True),
            bot_id=IntegerValue(bot_user.id),
            bot_username=StringValue(bot_user.username or ""),
        )


__all__ = (
    "TelegramHealthNode",
    "TelegramHealthOutput",
    "TelegramHealthParams",
)
