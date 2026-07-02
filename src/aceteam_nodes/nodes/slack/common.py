"""Shared Slack Web API helpers for aceteam-nodes."""

from typing import Any, Never

from slack_sdk.errors import SlackApiError, SlackClientError
from workflow_engine import StringValue, WorkflowException
from workflow_engine.core import StakeholderLevel

SLACK_BOT_TOKEN_ENV_VAR = "SLACK_BOT_TOKEN"
SLACK_USER_TOKEN_ENV_VAR = "SLACK_USER_TOKEN"

# Slack caps ``conversations.history`` / ``conversations.list`` at 200 per request.
_CONVERSATIONS_PAGE_LIMIT = 200


def require_string(value: str | None, field: str) -> StringValue:
    if value is None:
        raise WorkflowException(
            f"Slack response missing {field}.",
            level=StakeholderLevel.USER,
        )
    return StringValue(value)


def raise_slack_api_error(error: SlackApiError) -> Never:
    error_code = error.response.get("error", "unknown_error")
    raise WorkflowException(
        f"Slack rejected the request: {error_code}",
        level=StakeholderLevel.USER,
    ) from error


def raise_slack_client_error(error: SlackClientError) -> Never:
    raise WorkflowException(
        f"Failed to reach Slack: {error}",
        level=StakeholderLevel.USER,
    ) from error


def slack_error_code(response: Any) -> str:
    return str(response.get("error", "unknown_error"))


__all__ = (
    "SLACK_BOT_TOKEN_ENV_VAR",
    "SLACK_USER_TOKEN_ENV_VAR",
    "_CONVERSATIONS_PAGE_LIMIT",
    "raise_slack_api_error",
    "raise_slack_client_error",
    "require_string",
    "slack_error_code",
)
