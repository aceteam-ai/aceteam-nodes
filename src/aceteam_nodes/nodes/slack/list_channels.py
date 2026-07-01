"""Slack List Channels node - enumerates channels via ``conversations.list``."""

from typing import Any, ClassVar, Type

from overrides import override
from pydantic import Field
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.web.async_client import AsyncWebClient
from workflow_engine import (
    BooleanValue,
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
    OptionalIntegerValue,
    OptionalStringValue,
    optional_integer,
    optional_string,
    raise_slack_api_error,
    raise_slack_client_error,
    slack_error_code,
)

OptionalString = UnionValue[StringValue, NullValue]


class SlackListChannelsParams(Params):
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=IntegerValue(30),
    )


class SlackListChannelsInput(Data):
    types: OptionalString = Field(
        title="Types",
        description=(
            "Comma-separated channel types to include (e.g. ``public_channel,private_channel``)."
        ),
        default=OptionalString("public_channel,private_channel"),
    )


class SlackChannelItem(Data):
    channel_id: StringValue = Field(
        title="Channel ID",
        description="The channel ID (e.g. C0123).",
    )
    name: OptionalStringValue = Field(
        title="Name",
        description="The channel name without the leading #, when present.",
    )
    is_private: BooleanValue = Field(
        title="Is Private",
        description="Whether the channel is private.",
    )
    num_members: OptionalIntegerValue = Field(
        title="Member Count",
        description="The number of members in the channel, when reported by Slack.",
    )


class SlackListChannelsOutput(Data):
    channels: SequenceValue[DataValue[SlackChannelItem]] = Field(
        title="Channels",
        description="Channels visible to the bot token.",
    )


class SlackListChannelsNode(
    Node[
        SlackListChannelsInput,
        SlackListChannelsOutput,
        SlackListChannelsParams,
    ]
):
    """List workspace channels via ``conversations.list``."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Slack List Channels",
        description=(
            "Lists channels the bot can access via ``conversations.list``, "
            "paginating until the result set is exhausted."
        ),
        version="0.1.0",
        parameter_type=SlackListChannelsParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[SlackListChannelsInput]:
        return SlackListChannelsInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[SlackListChannelsOutput]:
        return SlackListChannelsOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[SlackListChannelsInput],
        output_type: Type[SlackListChannelsOutput],
        input: SlackListChannelsInput,
    ) -> SlackListChannelsOutput:
        token = await context.get_env(SLACK_BOT_TOKEN_ENV_VAR)
        timeout = self.params.timeout.root
        client = AsyncWebClient(token=token, timeout=timeout)

        types = input.types.root
        list_kwargs: dict[str, Any] = {}
        if types is not None:
            list_kwargs["types"] = types

        items: list[DataValue[SlackChannelItem]] = []
        cursor: str | None = None

        try:
            while True:
                response = await client.conversations_list(
                    **list_kwargs,
                    limit=_CONVERSATIONS_PAGE_LIMIT,
                    cursor=cursor,
                )
                if not response.get("ok", False):
                    raise WorkflowException(
                        f"Slack rejected the request: {slack_error_code(response)}",
                        level=StakeholderLevel.USER,
                    )

                for channel in response.get("channels", ()):
                    items.append(
                        DataValue[SlackChannelItem](
                            root=SlackChannelItem(
                                channel_id=StringValue(channel["id"]),
                                name=optional_string(channel.get("name")),
                                is_private=BooleanValue(bool(channel.get("is_private", False))),
                                num_members=optional_integer(channel.get("num_members")),
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
            channels=SequenceValue[DataValue[SlackChannelItem]](items),
        )


__all__ = (
    "SlackChannelItem",
    "SlackListChannelsInput",
    "SlackListChannelsNode",
    "SlackListChannelsOutput",
    "SlackListChannelsParams",
)
