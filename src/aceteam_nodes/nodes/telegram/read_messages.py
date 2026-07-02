"""Telegram Read Messages node - fetches recent updates via ``getUpdates``."""

from typing import ClassVar, Type

from overrides import override
from pydantic import Field
from telegram import Bot
from telegram.error import TelegramError
from workflow_engine import (
    Data,
    DataValue,
    DateValue,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    Params,
    SequenceValue,
)

from aceteam_nodes.utils import OptionalInteger, OptionalString, optional_integer, optional_string

from .common import (
    TELEGRAM_TOKEN_ENV_VAR,
    raise_telegram_api_error,
)

# Telegram caps ``getUpdates`` at 100 updates per request; not exposed on workflow input.
_GET_UPDATES_LIMIT = 100


class TelegramReadMessagesParams(Params):
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Long-poll timeout in seconds for ``getUpdates``.",
        default=IntegerValue(30),
    )


class TelegramReadMessagesInput(Data):
    offset: OptionalInteger = Field(
        title="Offset",
        description="Acknowledge and skip updates with an update id less than this value.",
        default=None,
    )


class TelegramMessageItem(Data):
    message_id: IntegerValue = Field(
        title="Message ID",
        description="The message id within the chat.",
    )
    chat_id: IntegerValue = Field(
        title="Chat ID",
        description="The chat the message was sent in.",
    )
    sender_id: OptionalInteger = Field(
        title="Sender ID",
        description="The sender's Telegram user id (``from`` in the Bot API), if present.",
    )
    sender_username: OptionalString = Field(
        title="Sender Username",
        description="The sender's @username, if set on their account.",
    )
    text: OptionalString = Field(
        title="Text",
        description=(
            "The message text body; null for stickers, photos, and other non-text messages."
        ),
    )
    date: DateValue = Field(
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
            "Fetches pending updates via the Bot API ``getUpdates`` long poll, "
            "paginating until the queue is exhausted. "
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
        poll_timeout = 0 if timeout < 1 else int(timeout)

        items: list[DataValue[TelegramMessageItem]] = []

        try:
            async with Bot(token=token) as bot:
                while True:
                    updates = await bot.get_updates(
                        offset=offset,
                        limit=_GET_UPDATES_LIMIT,
                        timeout=poll_timeout,
                        read_timeout=timeout,
                        write_timeout=timeout,
                        connect_timeout=timeout,
                    )
                    if not updates:
                        break

                    for update in updates:
                        message = update.message
                        if message is None:
                            continue
                        sender = message.from_user
                        items.append(
                            DataValue[TelegramMessageItem](
                                root=TelegramMessageItem(
                                    message_id=IntegerValue(message.message_id),
                                    chat_id=IntegerValue(message.chat_id),
                                    sender_id=optional_integer(
                                        None if sender is None else sender.id
                                    ),
                                    sender_username=optional_string(
                                        None if sender is None else sender.username
                                    ),
                                    text=optional_string(message.text),
                                    date=DateValue(message.date),
                                ),
                            ),
                        )

                    offset = updates[-1].update_id + 1
                    if len(updates) < _GET_UPDATES_LIMIT:
                        break
                    poll_timeout = 0
        except TelegramError as e:
            raise_telegram_api_error(e)

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
