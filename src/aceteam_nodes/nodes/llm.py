"""LLM node - AI text generation via aceteam-aep."""

from typing import ClassVar, Literal, Type

from overrides import override
from pydantic import Field
from workflow_engine import Data, ExecutionContext, Node, NodeTypeInfo, Params, StringValue

from ..context import CLIContext


class LLMNodeParams(Params):
    model: StringValue = Field(
        title="Model",
        default=StringValue("gpt-4o-mini"),
        description="The AI model to use for text generation",
    )
    system_prompt: StringValue = Field(
        title="System Prompt",
        default=StringValue("You are a helpful assistant."),
        description="System prompt to guide the AI's behavior",
    )


class LLMNodeInput(Data):
    prompt: StringValue = Field(
        title="Prompt",
        description="The prompt to send to the LLM.",
    )


class LLMNodeOutput(Data):
    response: StringValue = Field(
        title="Response",
        description="The response from the LLM.",
    )


class LLMNode(
    Node[LLMNodeInput, LLMNodeOutput, LLMNodeParams],
):
    """AI text generation node. Uses aceteam-aep for multi-provider support."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        name="LLM",
        display_name="LLM",
        description="Send a text prompt to an AI model and get a response.",
        version="1.0.0",
        parameter_type=LLMNodeParams,
    )

    type: Literal["LLM"] = "LLM"  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    @override
    def static_input_type(cls) -> Type[LLMNodeInput]:
        return LLMNodeInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[LLMNodeOutput]:
        return LLMNodeOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[LLMNodeInput],
        output_type: Type[LLMNodeOutput],
        input: LLMNodeInput,
    ) -> LLMNodeOutput:
        prompt_text = input.prompt.root
        model = self.params.model.root
        system_prompt = self.params.system_prompt.root

        assert isinstance(context, CLIContext)
        response_text = await context.call_llm(
            model=model,
            system_prompt=system_prompt,
            prompt=prompt_text,
        )

        return output_type(response=StringValue(response_text))


__all__ = [
    "LLMNode",
    "LLMNodeInput",
    "LLMNodeOutput",
    "LLMNodeParams",
]
