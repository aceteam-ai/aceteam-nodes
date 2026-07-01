"""Discord List Channels node - enumerates channels in a guild."""

from typing import ClassVar, Type

from discord.errors import DiscordException, HTTPException
from overrides import override
from pydantic import Field
from workflow_engine import (
    Data,
    DataValue,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    Params,
    SequenceValue,
    StringValue,
)

from .common import DISCORD_TOKEN_ENV_VAR, logged_in_discord_client, raise_discord_api_error


class DiscordListChannelsParams(Params):
    pass


class DiscordListChannelsInput(Data):
    guild_id: IntegerValue = Field(
        title="Guild ID",
        description="The server's snowflake ID.",
    )


class DiscordChannelItem(Data):
    channel_id: IntegerValue = Field(
        title="Channel ID",
        description="The channel snowflake ID.",
    )
    name: StringValue = Field(
        title="Name",
        description="The channel name.",
    )
    type: StringValue = Field(
        title="Type",
        description="The Discord channel type (e.g. text, voice, category).",
    )
    position: IntegerValue = Field(
        title="Position",
        description="The channel's sort position within the guild.",
    )


class DiscordListChannelsOutput(Data):
    channels: SequenceValue[DataValue[DiscordChannelItem]] = Field(
        title="Channels",
        description="Channels in the guild.",
    )


class DiscordListChannelsNode(
    Node[
        DiscordListChannelsInput,
        DiscordListChannelsOutput,
        DiscordListChannelsParams,
    ]
):
    """List channels in a Discord guild."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Discord List Channels",
        description="Enumerates channels in a Discord server (guild).",
        version="0.1.0",
        parameter_type=DiscordListChannelsParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[DiscordListChannelsInput]:
        return DiscordListChannelsInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[DiscordListChannelsOutput]:
        return DiscordListChannelsOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: type[DiscordListChannelsInput],
        output_type: type[DiscordListChannelsOutput],
        input: DiscordListChannelsInput,
    ) -> DiscordListChannelsOutput:
        token = await context.get_env(DISCORD_TOKEN_ENV_VAR)

        try:
            async with logged_in_discord_client(token) as client:
                guild = await client.fetch_guild(input.guild_id.root)
                raw_channels = await guild.fetch_channels()
        except HTTPException as e:
            raise_discord_api_error(self, e)
        except DiscordException as e:
            raise_discord_api_error(self, e)

        items = tuple(
            DataValue[DiscordChannelItem](
                root=DiscordChannelItem(
                    channel_id=IntegerValue(channel.id),
                    name=StringValue(channel.name),
                    type=StringValue(channel.type.name),
                    position=IntegerValue(channel.position),
                ),
            )
            for channel in raw_channels
        )

        return output_type(
            channels=SequenceValue[DataValue[DiscordChannelItem]](items),
        )


__all__ = (
    "DiscordChannelItem",
    "DiscordListChannelsInput",
    "DiscordListChannelsNode",
    "DiscordListChannelsOutput",
    "DiscordListChannelsParams",
)
