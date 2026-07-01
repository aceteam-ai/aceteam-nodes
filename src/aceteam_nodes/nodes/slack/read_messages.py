"""Slack Read Messages node - fetches channel history via ``conversations.history``."""

from typing import Any, ClassVar, Type

from overrides import override
from pydantic import Field
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.web.async_client import AsyncWebClient
from workflow_engine import (
    Data,
    DataValue,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    NullValue,
    Params,
    SequenceValue,
    StringValue,
    UnionValue,
    WorkflowException,
)
from workflow_engine.core import StakeholderLevel

from .common import (
    _CONVERSATIONS_PAGE_LIMIT,
    SLACK_BOT_TOKEN_ENV_VAR,
    OptionalStringValue,
    optional_string,
    raise_slack_api_error,
    raise_slack_client_error,
    slack_error_code,
)

OptionalString = UnionValue[StringValue, NullValue]


class SlackReadMessagesParams(Params):
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=IntegerValue(30),
    )


class SlackReadMessagesInput(Data):
    channel_id: StringValue = Field(
        title="Channel ID",
        description="The channel to read (e.g. C0123).",
    )
    oldest: OptionalString = Field(
        title="Oldest",
        description="Only messages after this Unix timestamp (exclusive).",
        default=OptionalString(None),
    )
    latest: OptionalString = Field(
        title="Latest",
        description="Only messages before this Unix timestamp (inclusive).",
        default=OptionalString(None),
    )


class SlackMessageItem(Data):
    ts: StringValue = Field(
        title="Timestamp",
        description="The message timestamp.",
    )
    user: OptionalStringValue = Field(
        title="User",
        description="The posting user's ID, when present.",
    )
    text: OptionalStringValue = Field(
        title="Text",
        description="The message text, when present.",
    )
    thread_ts: OptionalStringValue = Field(
        title="Thread Timestamp",
        description="The parent thread timestamp, when this message is a reply.",
    )


class SlackReadMessagesOutput(Data):
    messages: SequenceValue[DataValue[SlackMessageItem]] = Field(
        title="Messages",
        description="Channel messages in the requested window.",
    )


class SlackReadMessagesNode(
    Node[
        SlackReadMessagesInput,
        SlackReadMessagesOutput,
        SlackReadMessagesParams,
    ]
):
    """Fetch channel history via ``conversations.history``.

    Requires the ``channels:history`` and/or ``groups:history`` bot scopes.
    """

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Slack Read Messages",
        description=(
            "Fetches messages from a Slack channel via ``conversations.history``, "
            "paginating until the ``oldest``/``latest`` window is exhausted. "
            "Requires ``channels:history`` and/or ``groups:history`` scopes."
        ),
        version="0.1.0",
        parameter_type=SlackReadMessagesParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[SlackReadMessagesInput]:
        return SlackReadMessagesInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[SlackReadMessagesOutput]:
        return SlackReadMessagesOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[SlackReadMessagesInput],
        output_type: Type[SlackReadMessagesOutput],
        input: SlackReadMessagesInput,
    ) -> SlackReadMessagesOutput:
        token = await context.get_env(SLACK_BOT_TOKEN_ENV_VAR)
        timeout = self.params.timeout.root
        client = AsyncWebClient(token=token, timeout=timeout)

        oldest = input.oldest.root
        latest = input.latest.root
        history_kwargs: dict[str, Any] = {"channel": input.channel_id.root}
        if oldest is not None:
            history_kwargs["oldest"] = oldest
        if latest is not None:
            history_kwargs["latest"] = latest

        items: list[DataValue[SlackMessageItem]] = []
        cursor: str | None = None

        try:
            while True:
                response = await client.conversations_history(
                    **history_kwargs,
                    limit=_CONVERSATIONS_PAGE_LIMIT,
                    cursor=cursor,
                )
                if not response.get("ok", False):
                    raise WorkflowException(
                        f"Slack rejected the request: {slack_error_code(response)}",
                        level=StakeholderLevel.USER,
                    )

                for message in response.get("messages", ()):
                    items.append(
                        DataValue[SlackMessageItem](
                            root=SlackMessageItem(
                                ts=StringValue(message["ts"]),
                                user=optional_string(message.get("user")),
                                text=optional_string(message.get("text")),
                                thread_ts=optional_string(message.get("thread_ts")),
                            ),
                        ),
                    )

                cursor = response.get("response_metadata", {}).get("next_cursor") or None
                if not cursor:
                    break
        except SlackApiError as e:
            raise_slack_api_error(e)
        except SlackClientError as e:
            raise_slack_client_error(e)

        return output_type(
            messages=SequenceValue[DataValue[SlackMessageItem]](items),
        )


__all__ = (
    "SlackMessageItem",
    "SlackReadMessagesInput",
    "SlackReadMessagesNode",
    "SlackReadMessagesOutput",
    "SlackReadMessagesParams",
)
