"""Shared Telegram Bot API helpers for aceteam-nodes."""

from typing import Never, cast

from telegram.error import BadRequest, NetworkError, TelegramError
from workflow_engine import IntegerValue, NullValue, StringValue, UnionValue

TELEGRAM_TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"

OptionalIntegerValue = UnionValue[IntegerValue, NullValue]
OptionalStringValue = UnionValue[StringValue, NullValue]


def optional_integer(value: int | None) -> OptionalIntegerValue:
    member: IntegerValue | NullValue = (
        NullValue(None) if value is None else IntegerValue(value)
    )
    return cast(OptionalIntegerValue, member)


def optional_string(value: str | None) -> OptionalStringValue:
    member: StringValue | NullValue = NullValue(None) if value is None else StringValue(value)
    return cast(OptionalStringValue, member)


def raise_telegram_api_error(error: TelegramError) -> Never:
    from workflow_engine import WorkflowException
    from workflow_engine.core import StakeholderLevel

    if isinstance(error, BadRequest):
        raise WorkflowException(
            f"Telegram rejected the request: {error.message}",
            level=StakeholderLevel.USER,
        ) from error
    if isinstance(error, NetworkError):
        raise WorkflowException(
            f"Failed to reach Telegram: {error.message}",
            level=StakeholderLevel.USER,
        ) from error
    raise WorkflowException(
        f"Telegram rejected the request: {error.message}",
        level=StakeholderLevel.USER,
    ) from error
