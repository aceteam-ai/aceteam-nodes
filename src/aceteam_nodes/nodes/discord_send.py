"""Discord Send Message node - sends a message via the Discord REST API.

Mirrors the AceTeam ``discord_send_message`` MCP tool as a self-contained
workflow node. The bot token is resolved at runtime via ``context.get_env``
(never baked into the workflow definition), so the only platform coupling is
whatever the context chooses to back ``get_env`` with.
"""

import logging
from typing import ClassVar, Type

import discord
from discord.errors import DiscordException, HTTPException
from overrides import override
from pydantic import Field
from workflow_engine import (
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

_DISCORD_TOKEN_ENV_VAR = "DISCORD_BOT_TOKEN"


class DiscordSendMessageParams(Params):
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=IntegerValue(30),
    )


class DiscordSendMessageInput(Data):
    channel_id: StringValue = Field(
        title="Channel ID",
        description="The target channel's snowflake ID.",
    )
    content: StringValue = Field(
        title="Content",
        description="The message content to send.",
    )


class DiscordSendMessageOutput(Data):
    message_id: StringValue = Field(
        title="Message ID",
        description="The snowflake ID of the sent message.",
    )


class DiscordSendMessageNode(
    Node[
        DiscordSendMessageInput,
        DiscordSendMessageOutput,
        DiscordSendMessageParams,
    ]
):
    """Sends a message to a Discord channel via the REST API."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Discord Send Message",
        description="Sends a message to a Discord channel via the REST API.",
        version="0.1.0",
        parameter_type=DiscordSendMessageParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[DiscordSendMessageInput]:
        return DiscordSendMessageInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[DiscordSendMessageOutput]:
        return DiscordSendMessageOutput

    @override
    async def run(
        self,
        context: ExecutionContext,
        input: DiscordSendMessageInput,
    ) -> DiscordSendMessageOutput:
        token = await context.get_env(_DISCORD_TOKEN_ENV_VAR)
        client = discord.Client(intents=discord.Intents.none())

        await client.login(token)
        try:
            try:
                channel = await client.fetch_channel(int(input.channel_id.root))
                if not isinstance(channel, discord.abc.Messageable):
                    raise WorkflowException(
                        f"Channel {input.channel_id.root} cannot receive messages.",
                        level=StakeholderLevel.USER,
                    )
                message = await channel.send(input.content.root)
            except HTTPException as e:
                raise WorkflowException(
                    f"Discord rejected the message: {e.text}",
                    level=StakeholderLevel.USER,
                ) from e
            except DiscordException as e:
                raise WorkflowException(
                    f"Failed to reach Discord: {e}",
                    level=StakeholderLevel.USER,
                ) from e
        finally:
            await client.close()

        return DiscordSendMessageOutput(
            message_id=StringValue(str(message.id)),
        )


__all__ = (
    "DiscordSendMessageInput",
    "DiscordSendMessageNode",
    "DiscordSendMessageOutput",
    "DiscordSendMessageParams",
)
