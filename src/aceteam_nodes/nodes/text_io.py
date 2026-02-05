"""Text Input node - simple text source for workflows."""

from functools import cached_property
from typing import Literal

from overrides import override
from pydantic import Field
from workflow_engine import Context, Data, Empty, Params, StringValue
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo

from ..node_base import AceTeamNode


class TextInputNodeParams(Params):
    text: StringValue = Field(
        default=StringValue(""),
        description="The text content to output",
    )


class TextInputNodeOutput(Data):
    output: StringValue


class TextInputNode(
    AceTeamNode[Empty, TextInputNodeOutput, TextInputNodeParams],
):
    """A simple text source node that outputs a configurable text string."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="TextInput",
        display_name="Text Input",
        description="A simple text source.",
        version="1.0.0",
        parameter_type=TextInputNodeParams,
    )

    type: Literal["TextInput"] = "TextInput"

    @cached_property
    def output_type(self):
        return TextInputNodeOutput

    @override
    async def run(self, context: Context, input: Empty) -> TextInputNodeOutput:
        return TextInputNodeOutput(output=self.params.text)


__all__ = [
    "TextInputNode",
    "TextInputNodeOutput",
    "TextInputNodeParams",
]
