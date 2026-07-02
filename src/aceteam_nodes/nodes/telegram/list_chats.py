"""Telegram List Chats node - looks up metadata for a single chat via ``getChat``."""

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

from aceteam_nodes.utils import OptionalString, optional_string

from .common import TELEGRAM_TOKEN_ENV_VAR, raise_telegram_api_error


class TelegramListChatsParams(Params):
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=IntegerValue(30),
    )


class TelegramListChatsInput(Data):
    chat_id: StringValue = Field(
        title="Chat ID",
        description="The chat to look up: a numeric id or an @channelusername.",
    )


class TelegramListChatsOutput(Data):
    chat_id: IntegerValue = Field(
        title="Chat ID",
        description="The chat's numeric id.",
    )
    type: StringValue = Field(
        title="Type",
        description="The chat type (e.g. private, group, supergroup, channel).",
    )
    title: OptionalString = Field(
        title="Title",
        description="The chat title, when present.",
    )
    username: OptionalString = Field(
        title="Username",
        description="The chat @username, when present.",
    )
    description: OptionalString = Field(
        title="Description",
        description="The chat description, when present.",
    )


class TelegramListChatsNode(
    Node[
        TelegramListChatsInput,
        TelegramListChatsOutput,
        TelegramListChatsParams,
    ]
):
    """Look up metadata for one chat the bot can access.

    There is no Bot API endpoint to enumerate every chat a bot belongs to; this
    node wraps ``getChat`` for a single ``chat_id``.
    """

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Telegram List Chats",
        description=(
            "Looks up metadata for a single chat via ``getChat``. "
            "The Bot API cannot enumerate all chats a bot belongs to."
        ),
        version="0.1.0",
        parameter_type=TelegramListChatsParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[TelegramListChatsInput]:
        return TelegramListChatsInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[TelegramListChatsOutput]:
        return TelegramListChatsOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[TelegramListChatsInput],
        output_type: Type[TelegramListChatsOutput],
        input: TelegramListChatsInput,
    ) -> TelegramListChatsOutput:
        token = await context.get_env(TELEGRAM_TOKEN_ENV_VAR)
        timeout = float(self.params.timeout.root)

        try:
            async with Bot(token=token) as bot:
                chat = await bot.get_chat(
                    chat_id=input.chat_id.root,
                    read_timeout=timeout,
                    write_timeout=timeout,
                    connect_timeout=timeout,
                )
        except TelegramError as e:
            raise_telegram_api_error(e)

        return output_type(
            chat_id=IntegerValue(chat.id),
            type=StringValue(chat.type),
            title=optional_string(chat.title),
            username=optional_string(chat.username),
            description=optional_string(chat.description),
        )


__all__ = (
    "TelegramListChatsInput",
    "TelegramListChatsNode",
    "TelegramListChatsOutput",
    "TelegramListChatsParams",
)
