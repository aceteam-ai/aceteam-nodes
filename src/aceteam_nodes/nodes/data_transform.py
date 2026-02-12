"""Data Transform node - simple data transformation."""

from functools import cached_property
from typing import Literal

from overrides import override
from pydantic import Field
from workflow_engine import Context, Data, Node, NodeTypeInfo, Params, StringValue


class DataTransformNodeParams(Params):
    instruction: StringValue = Field(
        default=StringValue("Pass through unchanged"),
        description="Description of the transformation to apply",
    )


class DataTransformNodeInput(Data):
    input: StringValue = Field(description="The data to transform")


class DataTransformNodeOutput(Data):
    output: StringValue = Field(description="The transformed data")


class DataTransformNode(
    Node[DataTransformNodeInput, DataTransformNodeOutput, DataTransformNodeParams],
):
    """Processes and transforms input data based on configured instructions."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="DataTransform",
        display_name="Transform",
        description="Processes and transforms data.",
        version="1.0.0",
        parameter_type=DataTransformNodeParams,
    )

    type: Literal["DataTransform"] = "DataTransform"

    @cached_property
    def input_type(self):
        return DataTransformNodeInput

    @cached_property
    def output_type(self):
        return DataTransformNodeOutput

    @override
    async def run(self, context: Context, input: DataTransformNodeInput) -> DataTransformNodeOutput:
        # Pass through - transformation logic can be extended
        return DataTransformNodeOutput(output=input.input)


__all__ = [
    "DataTransformNode",
    "DataTransformNodeInput",
    "DataTransformNodeOutput",
    "DataTransformNodeParams",
]
