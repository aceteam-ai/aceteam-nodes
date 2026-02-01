"""Text Input node - simple text source for workflows."""

from collections.abc import Sequence
from typing import Literal

from overrides import override
from pydantic import Field
from workflow_engine import Context, Data, Params, StringValue
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo

from ..field import FieldInfo, FieldType
from ..node_base import AceTeamNode
from ..node_info import NodeTypeInfo


class TextInputNodeParams(Params):
    text: StringValue = Field(
        default=StringValue(""),
        description="The text content to output",
    )


class TextInputNodeOutput(Data):
    output: StringValue


class TextInputNode(
    AceTeamNode[None, TextInputNodeOutput, TextInputNodeParams],
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

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="TextInput",
            display_name="Text Input",
            description="A simple text source.",
            params=(
                FieldInfo(
                    name="text",
                    display_name="Text",
                    description="The text content to output",
                    type=FieldType.LONG_TEXT,
                    default="",
                ),
            ),
        )

    @property
    def input_fields_info(self) -> Sequence[FieldInfo]:
        return ()

    @property
    def output_fields_info(self) -> Sequence[FieldInfo]:
        return (
            FieldInfo(
                name="output",
                display_name="Output",
                description="The text content",
                type=FieldType.SHORT_TEXT,
            ),
        )

    @override
    async def run(self, context: Context, input: None) -> TextInputNodeOutput:
        return TextInputNodeOutput(output=self.params.text)


__all__ = [
    "TextInputNode",
    "TextInputNodeOutput",
    "TextInputNodeParams",
]
