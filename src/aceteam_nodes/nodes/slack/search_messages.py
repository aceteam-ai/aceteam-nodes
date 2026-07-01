"""Slack Search Messages node - searches workspace messages via ``search.messages``."""

from typing import ClassVar, Type

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
    Params,
    SequenceValue,
    StringValue,
    WorkflowException,
)
from workflow_engine.core import StakeholderLevel

from .common import (
    SLACK_USER_TOKEN_ENV_VAR,
    OptionalStringValue,
    optional_string,
    raise_slack_api_error,
    raise_slack_client_error,
    slack_error_code,
)


class SlackSearchMessagesParams(Params):
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=IntegerValue(30),
    )
    count: IntegerValue = Field(
        title="Count",
        description="Maximum number of matches to return per request (1-100).",
        default=IntegerValue(20),
    )


class SlackSearchMessagesInput(Data):
    query: StringValue = Field(
        title="Query",
        description="Slack search query syntax.",
    )


class SlackSearchMatchItem(Data):
    ts: StringValue = Field(
        title="Timestamp",
        description="The message timestamp.",
    )
    channel: OptionalStringValue = Field(
        title="Channel",
        description="The channel ID containing the match.",
    )
    user: OptionalStringValue = Field(
        title="User",
        description="The posting user's ID, when present.",
    )
    text: OptionalStringValue = Field(
        title="Text",
        description="The matched message text.",
    )
    permalink: OptionalStringValue = Field(
        title="Permalink",
        description="A permalink to the message, when present.",
    )


class SlackSearchMessagesOutput(Data):
    matches: SequenceValue[DataValue[SlackSearchMatchItem]] = Field(
        title="Matches",
        description="Messages matching the search query.",
    )


class SlackSearchMessagesNode(
    Node[
        SlackSearchMessagesInput,
        SlackSearchMessagesOutput,
        SlackSearchMessagesParams,
    ]
):
    """Search workspace messages via ``search.messages``.

    Requires a **user** token (``SLACK_USER_TOKEN``, ``xoxp-...``), not a bot token.
    """

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Slack Search Messages",
        description=(
            "Searches workspace messages via ``search.messages``. "
            "Requires a user token in ``SLACK_USER_TOKEN`` (``xoxp-...``), not "
            "``SLACK_BOT_TOKEN``."
        ),
        version="0.1.0",
        parameter_type=SlackSearchMessagesParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[SlackSearchMessagesInput]:
        return SlackSearchMessagesInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[SlackSearchMessagesOutput]:
        return SlackSearchMessagesOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[SlackSearchMessagesInput],
        output_type: Type[SlackSearchMessagesOutput],
        input: SlackSearchMessagesInput,
    ) -> SlackSearchMessagesOutput:
        token = await context.get_env(SLACK_USER_TOKEN_ENV_VAR)
        timeout = self.params.timeout.root
        count = self.params.count.root
        client = AsyncWebClient(token=token, timeout=timeout)

        try:
            response = await client.search_messages(
                query=input.query.root,
                count=count,
            )
            if not response.get("ok", False):
                raise WorkflowException(
                    f"Slack rejected the request: {slack_error_code(response)}",
                    level=StakeholderLevel.USER,
                )
        except SlackApiError as e:
            raise_slack_api_error(e)
        except SlackClientError as e:
            raise_slack_client_error(e)

        items: list[DataValue[SlackSearchMatchItem]] = []
        for match in response.get("messages", {}).get("matches", ()):
            channel = match.get("channel")
            channel_id = channel.get("id") if isinstance(channel, dict) else channel
            if not isinstance(channel_id, str):
                channel_id = None
            items.append(
                DataValue[SlackSearchMatchItem](
                    root=SlackSearchMatchItem(
                        ts=StringValue(match["ts"]),
                        channel=optional_string(channel_id),
                        user=optional_string(match.get("user")),
                        text=optional_string(match.get("text")),
                        permalink=optional_string(match.get("permalink")),
                    ),
                ),
            )

        return output_type(
            matches=SequenceValue[DataValue[SlackSearchMatchItem]](items),
        )


__all__ = (
    "SlackSearchMatchItem",
    "SlackSearchMessagesInput",
    "SlackSearchMessagesNode",
    "SlackSearchMessagesOutput",
    "SlackSearchMessagesParams",
)
