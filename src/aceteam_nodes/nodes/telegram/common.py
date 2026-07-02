"""Shared Telegram Bot API helpers for aceteam-nodes."""

from typing import Never

from telegram.error import BadRequest, NetworkError, TelegramError

TELEGRAM_TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"


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
