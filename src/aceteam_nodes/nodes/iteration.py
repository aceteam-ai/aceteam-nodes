"""ForEach iteration node."""

from collections.abc import Sequence
from functools import cached_property
from typing import Generic, Literal, Self, Type, TypeVar

from overrides import override
from pydantic import Field
from workflow_engine import (
    Context,
    Data,
    DataValue,
    Edge,
    Empty,
    InputEdge,
    IntegerValue,
    JSONValue,
    Node,
    OutputEdge,
    Params,
    SequenceValue,
    UserException,
    Value,
    ValueType,
    Workflow,
)
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo
from workflow_engine.core.values import build_data_type

from ..field import FieldInfo, FieldType
from ..node_base import AceTeamNode
from ..node_info import NodeTypeInfo
from ..workflow import AceTeamWorkflow

V = TypeVar("V", bound=Value)
D = TypeVar("D", bound=Data)


class SequenceParams(Params):
    length: IntegerValue


class SequenceData(Data, Generic[V]):
    sequence: SequenceValue[V]


class GatherSequenceNode(Node[Data, SequenceData, SequenceParams]):
    """Creates a sequence from indexed inputs."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="GatherSequence",
        display_name="Gather Sequence",
        description="Creates a sequence from indexed inputs.",
        version="0.4.0",
        parameter_type=SequenceParams,
    )

    type: Literal["GatherSequence"] = "GatherSequence"  # pyright: ignore[reportIncompatibleVariableOverride]
    element_type: ValueType = Field(default=Value, exclude=True)

    def key(self, index: int) -> str:
        return f"element_{index}"

    @property
    def keys(self) -> list[str]:
        N = self.params.length.root
        return [self.key(i) for i in range(N)]

    @property
    def input_type(self) -> Type[Data]:
        return build_data_type(
            "GatherSequenceInput",
            {key: (self.element_type, True) for key in self.keys},
        )

    @property
    def output_type(self) -> Type[SequenceData]:
        return SequenceData[self.element_type]

    @override
    async def run(self, context: Context, input: Data) -> SequenceData:
        input_dict = input.to_dict()
        return self.output_type(
            sequence=SequenceValue[self.element_type](root=[input_dict[key] for key in self.keys])
        )

    @classmethod
    def from_length(cls, id: str, length: int, element_type: ValueType = Value) -> Self:
        return cls(
            id=id,
            params=SequenceParams(length=IntegerValue(root=length)),
            element_type=element_type,
        )


class ExpandSequenceNode(Node[SequenceData, Data, SequenceParams]):
    """Extracts sequence elements into indexed outputs."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="ExpandSequence",
        display_name="Expand Sequence",
        description="Extracts sequence elements into indexed outputs.",
        version="0.4.0",
        parameter_type=SequenceParams,
    )

    type: Literal["ExpandSequence"] = "ExpandSequence"  # pyright: ignore[reportIncompatibleVariableOverride]
    element_type: ValueType = Value

    def key(self, index: int) -> str:
        return f"element_{index}"

    @property
    def keys(self) -> list[str]:
        N = self.params.length.root
        return [self.key(i) for i in range(N)]

    @property
    def input_type(self) -> Type[SequenceData]:
        return SequenceData[self.element_type]

    @property
    def output_type(self) -> Type[Data]:
        return build_data_type(
            "ExpandSequenceOutput",
            {key: (self.element_type, True) for key in self.keys},
        )

    @override
    async def run(self, context: Context, input: SequenceData) -> Data:
        N = self.params.length.root
        assert len(input.sequence) == N, (
            f"Expected sequence of length {N}, but got {len(input.sequence)}"
        )
        return self.output_type(**{self.key(i): input.sequence[i] for i in range(N)})

    @classmethod
    def from_length(cls, id: str, length: int, element_type: ValueType = Value) -> Self:
        return cls(
            id=id,
            params=SequenceParams(length=IntegerValue(root=length)),
            element_type=element_type,
        )


class NestedData(Data, Generic[D]):
    data: DataValue[D]


class GatherDataNode(Node[Data, NestedData, Empty]):
    """Gathers a data object into a nested `data` field."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="GatherData",
        display_name="Gather Data",
        description="Gathers a data object into a nested data field.",
        version="0.4.0",
        parameter_type=Empty,
    )

    type: Literal["GatherData"] = "GatherData"  # pyright: ignore[reportIncompatibleVariableOverride]
    data_type: Type[Data] = Field(default=Data, exclude=True)

    @property
    def input_type(self) -> Type[Data]:
        return self.data_type

    @property
    def output_type(self) -> Type[NestedData]:
        return NestedData[self.data_type]

    @override
    async def run(self, context: Context, input: Data) -> NestedData:
        return NestedData[self.data_type](data=DataValue[self.data_type](root=input))

    @classmethod
    def from_data_type(cls, id: str, data_type: Type[Data]) -> Self:
        return cls(id=id, params=Empty(), data_type=data_type)


class ExpandDataNode(Node[NestedData, Data, Empty]):
    """Expands a nested `data` object into its fields."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="ExpandData",
        display_name="Expand Data",
        description="Expands a nested data object into its fields.",
        version="0.4.0",
        parameter_type=Empty,
    )

    type: Literal["ExpandData"] = "ExpandData"  # pyright: ignore[reportIncompatibleVariableOverride]
    data_type: Type[Data] = Field(default=Data, exclude=True)

    @property
    def input_type(self) -> Type[NestedData]:
        return NestedData[self.data_type]

    @property
    def output_type(self) -> Type[Data]:
        return self.data_type

    @override
    async def run(self, context: Context, input: NestedData) -> Data:
        return input.data.root

    @classmethod
    def from_data_type(cls, id: str, data_type: Type[Data]) -> Self:
        return cls(id=id, params=Empty(), data_type=data_type)


class JsonToSequenceInput(Data):
    sequence: JSONValue


class JsonToSequenceOutput(Data, Generic[V]):
    sequence: SequenceValue[V]


class JsonToSequenceNode(Node[JsonToSequenceInput, JsonToSequenceOutput, Empty]):
    """Converts a JSON array into a typed sequence."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="JsonToSequence",
        display_name="Json to Sequence",
        description="Converts a JSON array into a typed sequence.",
        version="0.4.0",
        parameter_type=Empty,
    )

    type: Literal["JsonToSequence"] = "JsonToSequence"
    element_type: ValueType = Value
    data_type: Type[Data] = Field(default=Data, exclude=True)

    @property
    def input_type(self) -> Type[JsonToSequenceInput]:
        return JsonToSequenceInput

    @property
    def output_type(self) -> Type[JsonToSequenceOutput]:
        return JsonToSequenceOutput[DataValue[self.data_type]]

    @override
    async def run(self, context: Context, input: JsonToSequenceInput) -> JsonToSequenceOutput:
        items = input.sequence.root
        if not isinstance(items, Sequence):
            raise UserException(f"Expected a JSON sequence, but got {type(items)}: {items}")
        typed_items: list[DataValue] = []
        for item in items:
            typed_items.append(DataValue[self.data_type](root=self.data_type.model_validate(item)))
        return self.output_type(
            sequence=SequenceValue[DataValue[self.data_type]](root=typed_items)
        )

    @classmethod
    def from_data_type(cls, id: str, data_type: Type[Data]) -> Self:
        return cls(id=id, params=Empty(), data_type=data_type)


class ForEachParams(Params):
    workflow: JSONValue = Field(default_factory=lambda: JSONValue(None))

    @property
    def ace_workflow(self) -> AceTeamWorkflow:
        return AceTeamWorkflow.model_validate(self.workflow.root)


class ForEachNode(AceTeamNode[SequenceData, SequenceData, ForEachParams]):
    """Executes a nested workflow for each element in the input sequence."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="ForEach",
        display_name="For Each",
        description="Executes a nested workflow for each element in the input sequence.",
        version="0.4.0",
        parameter_type=ForEachParams,
    )

    type: Literal["ForEach"] = "ForEach"  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="ForEach",
            display_name="For Each",
            description="Executes a nested workflow for each element in the input sequence.",
            params=(
                FieldInfo(
                    name="workflow",
                    display_name="Workflow",
                    description="Workflow to run for each element.",
                    type=FieldType.WORKFLOW,
                ),
            ),
        )

    @cached_property
    def input_fields_info(self) -> Sequence[FieldInfo]:
        return (
            FieldInfo(
                name="sequence",
                display_name="Sequence",
                description="Sequence of items to process.",
                type=FieldType.JSON,
            ),
        )

    @cached_property
    def output_fields_info(self) -> Sequence[FieldInfo]:
        return (
            FieldInfo(
                name="sequence",
                display_name="Sequence",
                description="Processed sequence.",
                type=FieldType.JSON,
            ),
        )

    @override
    async def run(self, context: Context, input: Data) -> Workflow:
        seq = getattr(input, "sequence")
        N = len(seq.root)
        workflow = self.params.ace_workflow

        nodes: list[Node] = []
        edges: list[Edge] = []

        json_to_sequence = JsonToSequenceNode.from_data_type(
            id="json_to_sequence", data_type=workflow.input_type
        )
        expand = ExpandSequenceNode.from_length(
            id="expand", length=N, element_type=DataValue[workflow.input_type]
        )
        gather = GatherSequenceNode.from_length(
            id="gather", length=N, element_type=DataValue[workflow.output_type]
        )
        nodes.append(json_to_sequence)
        nodes.append(expand)
        nodes.append(gather)

        for i in range(N):
            namespace = f"element_{i}"
            input_adapter = ExpandDataNode.from_data_type(
                id="input_adapter", data_type=workflow.input_type
            ).with_namespace(namespace)
            item_workflow = workflow.with_namespace(namespace)
            output_adapter = GatherDataNode.from_data_type(
                id="output_adapter", data_type=workflow.output_type
            ).with_namespace(namespace)

            nodes.append(input_adapter)
            nodes.extend(item_workflow.nodes)
            nodes.append(output_adapter)

            edges.append(
                Edge.from_nodes(
                    source=expand, source_key=expand.key(i),
                    target=input_adapter, target_key="data",
                )
            )
            for input_edge in item_workflow.input_edges:
                edges.append(
                    Edge(
                        source_id=input_adapter.id, source_key=input_edge.input_key,
                        target_id=input_edge.target_id, target_key=input_edge.target_key,
                    )
                )
            edges.extend(item_workflow.edges)
            for output_edge in item_workflow.output_edges:
                edges.append(
                    Edge(
                        source_id=output_edge.source_id, source_key=output_edge.source_key,
                        target_id=output_adapter.id, target_key=output_edge.output_key,
                    )
                )
            edges.append(
                Edge.from_nodes(
                    source=output_adapter, source_key="data",
                    target=gather, target_key=gather.key(i),
                )
            )

        edges.append(
            Edge.from_nodes(
                source=json_to_sequence, source_key="sequence",
                target=expand, target_key="sequence",
            )
        )

        return Workflow(
            nodes=nodes,
            edges=edges,
            input_edges=[
                InputEdge.from_node(
                    input_key="sequence", target=json_to_sequence, target_key="sequence"
                )
            ],
            output_edges=[
                OutputEdge.from_node(
                    source=gather, source_key="sequence", output_key="sequence"
                )
            ],
        )


__all__ = [
    "ForEachNode",
    "ForEachParams",
]
