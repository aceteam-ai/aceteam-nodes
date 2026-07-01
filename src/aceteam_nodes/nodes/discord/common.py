"""Shared Discord client helpers for aceteam-nodes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Never

import discord
from discord.errors import DiscordException, HTTPException

if TYPE_CHECKING:
    from workflow_engine import Node

DISCORD_TOKEN_ENV_VAR = "DISCORD_BOT_TOKEN"


def discord_intents(*, message_content: bool = False) -> discord.Intents:
    if message_content:
        intents = discord.Intents.default()
        intents.message_content = True
        return intents
    return discord.Intents.none()


@asynccontextmanager
async def logged_in_discord_client(
    token: str,
    *,
    message_content: bool = False,
) -> AsyncIterator[discord.Client]:
    client = discord.Client(intents=discord_intents(message_content=message_content))
    async with client:
        await client.login(token)
        yield client


def raise_discord_api_error(
    node: "Node",
    error: HTTPException | DiscordException,
) -> Never:
    from workflow_engine import NodeException

    if isinstance(error, HTTPException):
        raise NodeException.for_user(
            f"Discord rejected the request: {error.text}",
            node=node,
        ) from error
    raise NodeException.for_user(
        f"Failed to reach Discord: {error}",
        node=node,
    ) from error
