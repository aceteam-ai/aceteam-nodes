"""Telegram Read Messages node - fetches recent updates via ``getUpdates``."""

from typing import ClassVar, Type

from overrides import override
from pydantic import Field
from telegram import Bot
from telegram.error import TelegramError
from workflow_engine import (
    Data,
    DataValue,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    NullValue,
    Params,
    SequenceValue,
    StringValue,
    UnionValue,
)

from .common import TELEGRAM_TOKEN_ENV_VAR, raise_telegram_api_error

OptionalOffset = UnionValue[IntegerValue, NullValue]


class TelegramReadMessagesParams(Params):
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Long-poll timeout in seconds for ``getUpdates``.",
        default=IntegerValue(30),
    )


class TelegramReadMessagesInput(Data):
    offset: OptionalOffset = Field(
        title="Offset",
        description="Acknowledge and skip updates with an update id less than this value.",
        default=OptionalOffset(None),
    )
    limit: IntegerValue = Field(
        title="Limit",
        description="Maximum number of updates to return (1-100).",
        default=IntegerValue(100),
    )


class TelegramMessageItem(Data):
    message_id: IntegerValue = Field(
        title="Message ID",
        description="The message id within the chat.",
    )
    chat_id: StringValue = Field(
        title="Chat ID",
        description="The chat the message was sent in.",
    )
    sender_id: IntegerValue = Field(
        title="Sender ID",
        description="The sender's Telegram user id (``from`` in the Bot API).",
    )
    sender_username: StringValue = Field(
        title="Sender Username",
        description="The sender's @username, if available.",
    )
    text: StringValue = Field(
        title="Text",
        description="The message text, if present.",
    )
    date: StringValue = Field(
        title="Date",
        description="When the message was sent (ISO 8601 UTC).",
    )


class TelegramReadMessagesOutput(Data):
    messages: SequenceValue[DataValue[TelegramMessageItem]] = Field(
        title="Messages",
        description="Messages extracted from the returned updates.",
    )


class TelegramReadMessagesNode(
    Node[
        TelegramReadMessagesInput,
        TelegramReadMessagesOutput,
        TelegramReadMessagesParams,
    ]
):
    """Fetch recent bot updates via the Bot API ``getUpdates`` long poll."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Telegram Read Messages",
        description=(
            "Fetches recent updates via the Bot API ``getUpdates`` long poll. "
            "``getUpdates`` and webhook mode are mutually exclusive for a given bot."
        ),
        version="0.1.0",
        parameter_type=TelegramReadMessagesParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[TelegramReadMessagesInput]:
        return TelegramReadMessagesInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[TelegramReadMessagesOutput]:
        return TelegramReadMessagesOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[TelegramReadMessagesInput],
        output_type: Type[TelegramReadMessagesOutput],
        input: TelegramReadMessagesInput,
    ) -> TelegramReadMessagesOutput:
        token = await context.get_env(TELEGRAM_TOKEN_ENV_VAR)
        timeout = float(self.params.timeout.root)
        offset = input.offset.root
        limit = input.limit.root

        try:
            async with Bot(token=token) as bot:
                updates = await bot.get_updates(
                    offset=offset,
                    limit=limit,
                    timeout=int(timeout),
                    read_timeout=timeout,
                    write_timeout=timeout,
                    connect_timeout=timeout,
                )
        except TelegramError as e:
            raise_telegram_api_error(e)

        items: list[DataValue[TelegramMessageItem]] = []
        for update in updates:
            message = update.message
            if message is None:
                continue
            sender = message.from_user
            items.append(
                DataValue[TelegramMessageItem](
                    root=TelegramMessageItem(
                        message_id=IntegerValue(message.message_id),
                        chat_id=StringValue(str(message.chat_id)),
                        sender_id=IntegerValue(sender.id if sender is not None else 0),
                        sender_username=StringValue(
                            sender.username if sender is not None and sender.username else ""
                        ),
                        text=StringValue(message.text or ""),
                        date=StringValue(message.date.isoformat()),
                    ),
                ),
            )

        return output_type(
            messages=SequenceValue[DataValue[TelegramMessageItem]](items),
        )


__all__ = (
    "TelegramMessageItem",
    "TelegramReadMessagesInput",
    "TelegramReadMessagesNode",
    "TelegramReadMessagesOutput",
    "TelegramReadMessagesParams",
)
