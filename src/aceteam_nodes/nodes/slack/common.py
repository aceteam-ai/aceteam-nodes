"""Shared Slack Web API helpers for aceteam-nodes."""

from typing import Any, Never, cast

from slack_sdk.errors import SlackApiError, SlackClientError
from workflow_engine import IntegerValue, NullValue, StringValue, UnionValue, WorkflowException
from workflow_engine.core import StakeholderLevel

SLACK_BOT_TOKEN_ENV_VAR = "SLACK_BOT_TOKEN"
SLACK_USER_TOKEN_ENV_VAR = "SLACK_USER_TOKEN"

OptionalStringValue = UnionValue[StringValue, NullValue]
OptionalIntegerValue = UnionValue[IntegerValue, NullValue]

# Slack caps ``conversations.history`` / ``conversations.list`` at 200 per request.
_CONVERSATIONS_PAGE_LIMIT = 200


def optional_string(value: str | None) -> OptionalStringValue:
    member: StringValue | NullValue = NullValue(None) if value is None else StringValue(value)
    return cast(OptionalStringValue, member)


def optional_integer(value: int | None) -> OptionalIntegerValue:
    member: IntegerValue | NullValue = NullValue(None) if value is None else IntegerValue(value)
    return cast(OptionalIntegerValue, member)


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
    "OptionalIntegerValue",
    "OptionalStringValue",
    "optional_integer",
    "optional_string",
    "raise_slack_api_error",
    "raise_slack_client_error",
    "slack_error_code",
)
