"""Slack List Channels node - enumerates channels via ``conversations.list``."""
from __future__ import annotations

from typing import Any, ClassVar, Type

from overrides import override
from pydantic import Field
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.web.async_client import AsyncWebClient
from workflow_engine import (
    BooleanValue,
    Data,
    DataValue,
    Empty,
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

from aceteam_nodes.utils import OptionalInteger, optional_integer

from .common import (
    _CONVERSATIONS_PAGE_LIMIT,
    SLACK_BOT_TOKEN_ENV_VAR,
    raise_slack_api_error,
    raise_slack_client_error,
    require_string,
    slack_error_code,
)

_CHANNEL_TYPE_PUBLIC = "public_channel"
_CHANNEL_TYPE_PRIVATE = "private_channel"
_CHANNEL_TYPE_MPIM = "mpim"
_CHANNEL_TYPE_IM = "im"


def _channel_types_argument(params: SlackListChannelsParams) -> str:
    types: list[str] = []
    if params.include_public_channels.root:
        types.append(_CHANNEL_TYPE_PUBLIC)
    if params.include_private_channels.root:
        types.append(_CHANNEL_TYPE_PRIVATE)
    if params.include_multi_person_direct_messages.root:
        types.append(_CHANNEL_TYPE_MPIM)
    if params.include_one_to_one_direct_messages.root:
        types.append(_CHANNEL_TYPE_IM)
    if not types:
        raise WorkflowException(
            "At least one channel type must be enabled.",
            level=StakeholderLevel.USER,
        )
    return ",".join(types)


class SlackListChannelsParams(Params):
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=IntegerValue(30),
    )
    include_public_channels: BooleanValue = Field(
        title="Public Channels",
        description="Include public channels in the listing.",
        default=BooleanValue(True),
    )
    include_private_channels: BooleanValue = Field(
        title="Private Channels",
        description="Include private channels in the listing.",
        default=BooleanValue(True),
    )
    include_multi_person_direct_messages: BooleanValue = Field(
        title="Multi-Person DMs",
        description="Include multi-person direct messages in the listing.",
        default=BooleanValue(False),
    )
    include_one_to_one_direct_messages: BooleanValue = Field(
        title="Direct Messages",
        description="Include one-to-one direct messages in the listing.",
        default=BooleanValue(False),
    )


class SlackChannelItem(Data):
    channel_id: StringValue = Field(
        title="Channel ID",
        description="The channel ID (e.g. C0123).",
    )
    name: StringValue = Field(
        title="Name",
        description="The channel name without the leading #.",
    )
    is_private: BooleanValue = Field(
        title="Is Private",
        description="Whether the channel is private.",
    )
    num_members: OptionalInteger = Field(
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
        Empty,
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
        version="0.2.0",
        parameter_type=SlackListChannelsParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[Empty]:
        return Empty

    @classmethod
    @override
    def static_output_type(cls) -> Type[SlackListChannelsOutput]:
        return SlackListChannelsOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[Empty],
        output_type: Type[SlackListChannelsOutput],
        input: Empty,
    ) -> SlackListChannelsOutput:
        token = await context.get_env(SLACK_BOT_TOKEN_ENV_VAR)
        timeout = self.params.timeout.root
        client = AsyncWebClient(token=token, timeout=timeout)

        types = _channel_types_argument(self.params)
        list_kwargs: dict[str, Any] = {"types": types}

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
                                channel_id=require_string(channel.get("id"), "channel id"),
                                name=require_string(channel.get("name"), "channel name"),
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
    "SlackListChannelsNode",
    "SlackListChannelsOutput",
    "SlackListChannelsParams",
)
