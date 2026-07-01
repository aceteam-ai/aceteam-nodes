"""Slack Send Message node - posts a message via the Slack Web API."""

from typing import ClassVar, Type

from overrides import override
from pydantic import Field
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.web.async_client import AsyncWebClient
from workflow_engine import (
    Data,
    ExecutionContext,
    IntegerValue,
    Node,
    NodeTypeInfo,
    Params,
    StringValue,
)

from .common import (
    SLACK_BOT_TOKEN_ENV_VAR,
    raise_slack_api_error,
    raise_slack_client_error,
)


class SlackSendMessageParams(Params):
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
    channel: StringValue = Field(
        title="Channel",
        description="The channel the message was posted to.",
    )
    timestamp: StringValue = Field(
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
        self,
        *,
        context: ExecutionContext,
        input_type: Type[SlackSendMessageInput],
        output_type: Type[SlackSendMessageOutput],
        input: SlackSendMessageInput,
    ) -> SlackSendMessageOutput:
        token = await context.get_env(SLACK_BOT_TOKEN_ENV_VAR)
        timeout = self.params.timeout.root
        client = AsyncWebClient(token=token, timeout=timeout)

        try:
            response = await client.chat_postMessage(
                channel=input.channel.root,
                text=input.text.root,
            )
        except SlackApiError as e:
            raise_slack_api_error(e)
        except SlackClientError as e:
            raise_slack_client_error(e)

        return output_type(
            channel=StringValue(response.get("channel", input.channel.root)),
            timestamp=StringValue(response.get("ts", "")),
        )


__all__ = (
    "SlackSendMessageInput",
    "SlackSendMessageNode",
    "SlackSendMessageOutput",
    "SlackSendMessageParams",
)
