"""CSV Reader node - reads CSV data."""

from collections.abc import Sequence
from typing import Literal

from overrides import override
from pydantic import Field
from workflow_engine import Context, Data, Params, StringValue
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo

from ..field import FieldInfo, FieldType
from ..node_base import AceTeamNode
from ..node_info import NodeTypeInfo


class CSVReaderNodeParams(Params):
    sample_data: StringValue = Field(
        default=StringValue("name,value\nexample,1"),
        description="Embedded CSV data",
    )


class CSVReaderNodeOutput(Data):
    data: StringValue


class CSVReaderNode(
    AceTeamNode[None, CSVReaderNodeOutput, CSVReaderNodeParams],
):
    """Reads CSV data and outputs it as text."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="CSVReader",
        display_name="CSV Reader",
        description="Reads CSV data and outputs it as text.",
        version="1.0.0",
        parameter_type=CSVReaderNodeParams,
    )

    type: Literal["CSVReader"] = "CSVReader"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="CSVReader",
            display_name="CSV Reader",
            description="Reads CSV data and outputs it as text.",
            params=(
                FieldInfo(
                    name="sample_data",
                    display_name="Sample Data",
                    description="Embedded CSV data",
                    type=FieldType.LONG_TEXT,
                    default="name,value\nexample,1",
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
                name="data",
                display_name="Data",
                description="The CSV data as text",
                type=FieldType.LONG_TEXT,
            ),
        )

    @override
    async def run(self, context: Context, input: None) -> CSVReaderNodeOutput:
        return CSVReaderNodeOutput(data=self.params.sample_data)


__all__ = [
    "CSVReaderNode",
    "CSVReaderNodeOutput",
    "CSVReaderNodeParams",
]
