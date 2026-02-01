"""LLM node - AI text generation via litellm."""

from collections.abc import Sequence
from typing import Literal

from overrides import override
from pydantic import Field
from workflow_engine import Context, Data, Params, StringValue
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo

from ..context import CLIContext
from ..field import FieldInfo, FieldType
from ..node_base import AceTeamNode
from ..node_info import NodeTypeInfo


class LLMNodeParams(Params):
    model: StringValue = Field(
        default=StringValue("gpt-4o-mini"),
        description="The AI model to use for text generation",
    )
    system_prompt: StringValue = Field(
        default=StringValue("You are a helpful assistant."),
        description="System prompt to guide the AI's behavior",
    )


class LLMNodeInput(Data):
    prompt: StringValue


class LLMNodeOutput(Data):
    response: StringValue


class LLMNode(
    AceTeamNode[LLMNodeInput, LLMNodeOutput, LLMNodeParams],
):
    """AI text generation node. Uses litellm for multi-provider support."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="LLM",
        display_name="LLM",
        description="Send a text prompt to an AI model and get a response.",
        version="1.0.0",
        parameter_type=LLMNodeParams,
    )

    type: Literal["LLM"] = "LLM"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="LLM",
            display_name="LLM",
            description="Send a text prompt to an AI model and get a response.",
            params=(
                FieldInfo(
                    name="model",
                    display_name="Model",
                    description="The AI model to use",
                    type=FieldType.SHORT_TEXT,
                    default="gpt-4o-mini",
                    options=("gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-latest"),
                ),
                FieldInfo(
                    name="system_prompt",
                    display_name="System Prompt",
                    description="System prompt to guide the AI's behavior",
                    type=FieldType.LONG_TEXT,
                    default="You are a helpful assistant.",
                ),
            ),
        )

    @property
    def input_fields_info(self) -> Sequence[FieldInfo]:
        return (
            FieldInfo(
                name="prompt",
                display_name="Prompt",
                description="The text prompt to send to the AI model",
                type=FieldType.LONG_TEXT,
            ),
        )

    @property
    def output_fields_info(self) -> Sequence[FieldInfo]:
        return (
            FieldInfo(
                name="response",
                display_name="Response",
                description="The AI-generated response",
                type=FieldType.LONG_TEXT,
            ),
        )

    @override
    async def run(self, context: Context, input: LLMNodeInput) -> LLMNodeOutput:
        prompt_text = input.prompt.root
        model = self.params.model.root
        system_prompt = self.params.system_prompt.root

        if isinstance(context, CLIContext):
            response_text = await context.call_llm(
                model=model,
                system_prompt=system_prompt,
                prompt=prompt_text,
            )
        else:
            # Fallback stub for non-CLI contexts
            response_text = f"[LLM response to: {prompt_text[:100]}...]"

        return LLMNodeOutput(response=StringValue(response_text))


__all__ = [
    "LLMNode",
    "LLMNodeInput",
    "LLMNodeOutput",
    "LLMNodeParams",
]
