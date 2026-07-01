"""Discord Read Messages node - fetches recent messages from a channel."""

from typing import ClassVar, Type

import discord
from discord.errors import DiscordException, HTTPException
from overrides import override
from pydantic import Field
from workflow_engine import (
    Data,
    DataValue,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeException,
    NodeTypeInfo,
    NullValue,
    Params,
    SequenceValue,
    StringValue,
    UnionValue,
)

from .common import DISCORD_TOKEN_ENV_VAR, logged_in_discord_client, raise_discord_api_error

OptionalSnowflake = UnionValue[IntegerValue, NullValue]


class DiscordReadMessagesParams(Params):
    pass


class DiscordReadMessagesInput(Data):
    channel_id: IntegerValue = Field(
        title="Channel ID",
        description="The target channel's snowflake ID.",
    )
    before: OptionalSnowflake = Field(
        title="Before",
        description="Return messages before this message snowflake ID.",
        default=OptionalSnowflake(None),
    )
    after: OptionalSnowflake = Field(
        title="After",
        description="Return messages after this message snowflake ID.",
        default=OptionalSnowflake(None),
    )


class DiscordMessageItem(Data):
    message_id: IntegerValue = Field(
        title="Message ID",
        description="The message snowflake ID.",
    )
    author_id: IntegerValue = Field(
        title="Author ID",
        description="The author's snowflake ID.",
    )
    author_name: StringValue = Field(
        title="Author Name",
        description="The author's display name.",
    )
    content: StringValue = Field(
        title="Content",
        description=(
            "The message text. Requires the Message Content privileged intent "
            "in the Discord Developer Portal; otherwise this is often empty."
        ),
    )
    created_at: StringValue = Field(
        title="Created At",
        description="When the message was created (ISO 8601 UTC).",
    )


class DiscordReadMessagesOutput(Data):
    messages: SequenceValue[DataValue[DiscordMessageItem]] = Field(
        title="Messages",
        description="Channel messages in the requested window, newest first by default.",
    )


class DiscordReadMessagesNode(
    Node[
        DiscordReadMessagesInput,
        DiscordReadMessagesOutput,
        DiscordReadMessagesParams,
    ]
):
    """Fetch recent messages from a Discord channel via ``channel.history``."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Discord Read Messages",
        description=(
            "Fetches messages from a Discord channel, paginating until the "
            "``before``/``after`` window is exhausted. Enable the Message Content "
            "privileged intent for the bot in the Discord Developer Portal or "
            "``content`` will usually be empty."
        ),
        version="0.1.0",
        parameter_type=DiscordReadMessagesParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[DiscordReadMessagesInput]:
        return DiscordReadMessagesInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[DiscordReadMessagesOutput]:
        return DiscordReadMessagesOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[DiscordReadMessagesInput],
        output_type: Type[DiscordReadMessagesOutput],
        input: DiscordReadMessagesInput,
    ) -> DiscordReadMessagesOutput:
        token = await context.get_env(DISCORD_TOKEN_ENV_VAR)

        try:
            async with logged_in_discord_client(token, message_content=True) as client:
                channel = await client.fetch_channel(input.channel_id.root)
                if not isinstance(channel, discord.abc.Messageable):
                    raise NodeException.for_user(
                        f"Channel {input.channel_id.root} does not support reading history.",
                        node=self,
                    )

                before_id = input.before.root
                after_id = input.after.root
                before = discord.Object(id=before_id) if before_id is not None else None
                after = discord.Object(id=after_id) if after_id is not None else None

                items: list[DataValue[DiscordMessageItem]] = []
                async for message in channel.history(
                    limit=None,
                    before=before,
                    after=after,
                ):
                    items.append(
                        DataValue[DiscordMessageItem](
                            root=DiscordMessageItem(
                                message_id=IntegerValue(message.id),
                                author_id=IntegerValue(message.author.id),
                                author_name=StringValue(message.author.display_name),
                                content=StringValue(message.content),
                                created_at=StringValue(message.created_at.isoformat()),
                            ),
                        ),
                    )
        except HTTPException as e:
            raise_discord_api_error(self, e)
        except DiscordException as e:
            raise_discord_api_error(self, e)

        return output_type(
            messages=SequenceValue[DataValue[DiscordMessageItem]](items),
        )


__all__ = (
    "DiscordMessageItem",
    "DiscordReadMessagesInput",
    "DiscordReadMessagesNode",
    "DiscordReadMessagesOutput",
    "DiscordReadMessagesParams",
)
