"""Discord Bot Info node - returns the authenticated bot's identity."""

from typing import ClassVar, Type

from discord.errors import DiscordException, HTTPException
from overrides import override
from pydantic import Field
from workflow_engine import (
    Data,
    Empty,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    Params,
    StringValue,
)

from .common import DISCORD_TOKEN_ENV_VAR, logged_in_discord_client, raise_discord_api_error


class DiscordBotInfoParams(Params):
    pass


class DiscordBotInfoOutput(Data):
    bot_id: IntegerValue = Field(
        title="Bot ID",
        description="The bot user's snowflake ID.",
    )
    bot_username: StringValue = Field(
        title="Bot Username",
        description="The bot user's username.",
    )


class DiscordBotInfoNode(
    Node[
        Empty,
        DiscordBotInfoOutput,
        DiscordBotInfoParams,
    ]
):
    """Return the bot identity for ``DISCORD_BOT_TOKEN`` after login."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Discord Bot Info",
        description="Returns the authenticated Discord bot's ID and username.",
        version="0.1.0",
        parameter_type=DiscordBotInfoParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[Empty]:
        return Empty

    @classmethod
    @override
    def static_output_type(cls) -> Type[DiscordBotInfoOutput]:
        return DiscordBotInfoOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[Empty],
        output_type: Type[DiscordBotInfoOutput],
        input: Empty,
    ) -> DiscordBotInfoOutput:
        token = await context.get_env(DISCORD_TOKEN_ENV_VAR)

        try:
            async with logged_in_discord_client(token) as client:
                await client.application_info()
                bot_user = client.user
                if bot_user is None:
                    raise DiscordException("Login succeeded but bot user is unavailable.")

            return output_type(
                bot_id=IntegerValue(bot_user.id),
                bot_username=StringValue(bot_user.name),
            )
        except HTTPException as e:
            raise_discord_api_error(self, e)
        except DiscordException as e:
            raise_discord_api_error(self, e)


__all__ = (
    "DiscordBotInfoNode",
    "DiscordBotInfoOutput",
    "DiscordBotInfoParams",
)
