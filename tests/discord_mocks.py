"""Shared Discord API mocks for unit tests."""

from discord.errors import Forbidden


def forbidden(message: str) -> Forbidden:
    error = Forbidden.__new__(Forbidden)
    error.text = message
    error.status = 403
    return error
