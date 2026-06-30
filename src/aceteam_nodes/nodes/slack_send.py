"""Slack Send Message node - posts a message via the Slack Web API.

Mirrors the AceTeam ``slack_send_message`` MCP tool as a self-contained
workflow node. The bot token is resolved at runtime via ``context.get_env``
(never baked into the workflow definition), so the only platform coupling is
whatever the context chooses to back ``get_env`` with.
"""

import logging
from typing import ClassVar, Type

from overrides import override
from pydantic import Field
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.web.async_client import AsyncWebClient
from workflow_engine import (
    BooleanValue,
    Data,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    Params,
    StringValue,
    WorkflowException,
)
from workflow_engine.core import StakeholderLevel

logger = logging.getLogger(__name__)


class SlackSendMessageParams(Params):
    bot_token_env: StringValue = Field(
        title="Bot Token Env Var",
        description=(
            "Name of the environment variable holding the Slack bot token. "
            "The token itself is resolved at runtime, not stored in the workflow."
        ),
        default=StringValue("SLACK_BOT_TOKEN"),
    )
    timeout: IntegerValue = Field(
        title="Timeout",
        description="Request timeout in seconds.",
        default=IntegerValue(30),
    )


class SlackSendMessageInput(Data):
    channel: StringValue = Field(
        title="Channel",
        description="Target channel: an ID (e.g. C0123) or a #channel name.",
    )
    text: StringValue = Field(
        title="Text",
        description="The message text to post.",
    )


class SlackSendMessageOutput(Data):
    ok: BooleanValue = Field(
        title="OK",
        description="Whether Slack accepted the message.",
    )
    channel: StringValue = Field(
        title="Channel",
        description="The channel the message was posted to.",
    )
    ts: StringValue = Field(
        title="Timestamp",
        description="The message timestamp, used to reference it later.",
    )


class SlackSendMessageNode(
    Node[
        SlackSendMessageInput,
        SlackSendMessageOutput,
        SlackSendMessageParams,
    ]
):
    """Posts a message to a Slack channel via the Web API ``chat.postMessage`` method."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Slack Send Message",
        description="Posts a message to a Slack channel via the Web API.",
        version="0.1.0",
        parameter_type=SlackSendMessageParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[SlackSendMessageInput]:
        return SlackSendMessageInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[SlackSendMessageOutput]:
        return SlackSendMessageOutput

    @override
    async def run(
        self, context: ExecutionContext, input: SlackSendMessageInput
    ) -> SlackSendMessageOutput:
        token = await context.get_env(self.params.bot_token_env.root)
        timeout = self.params.timeout.root
        client = AsyncWebClient(token=token, timeout=timeout)

        try:
            response = await client.chat_postMessage(
                channel=input.channel.root,
                text=input.text.root,
            )
        except SlackApiError as e:
            raise WorkflowException(
                f"Slack rejected the message: {e.response['error']}",
                level=StakeholderLevel.USER,
            ) from e
        except SlackClientError as e:
            raise WorkflowException(
                f"Failed to reach Slack: {e}",
                level=StakeholderLevel.USER,
            ) from e

        return SlackSendMessageOutput(
            ok=BooleanValue(True),
            channel=StringValue(response.get("channel", input.channel.root)),
            ts=StringValue(response.get("ts", "")),
        )


__all__ = (
    "SlackSendMessageInput",
    "SlackSendMessageNode",
    "SlackSendMessageOutput",
    "SlackSendMessageParams",
)
