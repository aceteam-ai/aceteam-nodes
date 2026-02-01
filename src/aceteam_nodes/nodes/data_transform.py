"""Data Transform node - simple data transformation."""

from collections.abc import Sequence
from typing import Literal

from overrides import override
from pydantic import Field
from workflow_engine import Context, Data, Params, StringValue
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo

from ..field import FieldInfo, FieldType
from ..node_base import AceTeamNode
from ..node_info import NodeTypeInfo


class DataTransformNodeParams(Params):
    instruction: StringValue = Field(
        default=StringValue("Pass through unchanged"),
        description="Description of the transformation to apply",
    )


class DataTransformNodeInput(Data):
    input: StringValue


class DataTransformNodeOutput(Data):
    output: StringValue


class DataTransformNode(
    AceTeamNode[DataTransformNodeInput, DataTransformNodeOutput, DataTransformNodeParams],
):
    """Processes and transforms input data based on configured instructions."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="DataTransform",
        display_name="Transform",
        description="Processes and transforms data.",
        version="1.0.0",
        parameter_type=DataTransformNodeParams,
    )

    type: Literal["DataTransform"] = "DataTransform"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="DataTransform",
            display_name="Transform",
            description="Processes and transforms data.",
            params=(
                FieldInfo(
                    name="instruction",
                    display_name="Instruction",
                    description="Description of the transformation to apply",
                    type=FieldType.LONG_TEXT,
                    default="Pass through unchanged",
                ),
            ),
        )

    @property
    def input_fields_info(self) -> Sequence[FieldInfo]:
        return (
            FieldInfo(
                name="input",
                display_name="Input",
                description="The data to transform",
                type=FieldType.LONG_TEXT,
            ),
        )

    @property
    def output_fields_info(self) -> Sequence[FieldInfo]:
        return (
            FieldInfo(
                name="output",
                display_name="Output",
                description="The transformed data",
                type=FieldType.LONG_TEXT,
            ),
        )

    @override
    async def run(
        self, context: Context, input: DataTransformNodeInput
    ) -> DataTransformNodeOutput:
        # Pass through - transformation logic can be extended
        return DataTransformNodeOutput(output=input.input)


__all__ = [
    "DataTransformNode",
    "DataTransformNodeInput",
    "DataTransformNodeOutput",
    "DataTransformNodeParams",
]
