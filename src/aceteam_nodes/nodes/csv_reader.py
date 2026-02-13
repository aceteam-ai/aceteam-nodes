"""CSV Reader node - reads CSV data."""

from functools import cached_property
from typing import Literal

from overrides import override
from pydantic import Field
from workflow_engine import Context, Data, Empty, Node, NodeTypeInfo, Params, StringValue


class CSVReaderNodeParams(Params):
    sample_data: StringValue = Field(
        default=StringValue("name,value\nexample,1"),
        description="Embedded CSV data",
    )


class CSVReaderNodeOutput(Data):
    data: StringValue = Field(
        description="The CSV data as text",
    )


class CSVReaderNode(
    Node[Empty, CSVReaderNodeOutput, CSVReaderNodeParams],
):
    """Reads CSV data and outputs it as text."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="CSVReader",
        display_name="CSV Reader",
        description="Reads CSV data and outputs it as text.",
        version="1.0.0",
        parameter_type=CSVReaderNodeParams,
    )

    type: Literal["CSVReader"] = "CSVReader"

    @cached_property
    def output_type(self):
        return CSVReaderNodeOutput

    @override
    async def run(self, context: Context, input: Empty) -> CSVReaderNodeOutput:
        return CSVReaderNodeOutput(data=self.params.sample_data)


__all__ = [
    "CSVReaderNode",
    "CSVReaderNodeOutput",
    "CSVReaderNodeParams",
]
