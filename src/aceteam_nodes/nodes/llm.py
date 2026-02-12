"""LLM node - AI text generation via litellm."""

from functools import cached_property
from typing import Literal

from overrides import override
from pydantic import Field
from workflow_engine import Context, Data, Node, NodeTypeInfo, Params, StringValue

from ..context import CLIContext


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
    Node[LLMNodeInput, LLMNodeOutput, LLMNodeParams],
):
    """AI text generation node. Uses litellm for multi-provider support."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="LLM",
        display_name="LLM",
        description="Send a text prompt to an AI model and get a response.",
        version="1.0.0",
        parameter_type=LLMNodeParams,
    )

    type: Literal["LLM"] = "LLM"

    @cached_property
    def input_type(self):
        return LLMNodeInput

    @cached_property
    def output_type(self):
        return LLMNodeOutput

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
