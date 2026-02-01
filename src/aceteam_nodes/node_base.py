"""AceTeam node base class with auto-registration."""

from collections.abc import Mapping, Sequence
from functools import cached_property
from typing import Any, Generic, Type, TypeVar

from workflow_engine import Data, DataMapping, Node, Params
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo

from .field import FieldInfo, build_pydantic_model
from .node_info import NodeTypeInfo

Input_contra = TypeVar("Input_contra", bound=Data, contravariant=True)
Output_co = TypeVar("Output_co", bound=Data, covariant=True)
Params_co = TypeVar("Params_co", bound=Params, covariant=True)


class AceTeamNode(
    Node[Input_contra, Output_co, Params_co],
    Generic[Input_contra, Output_co, Params_co],
):
    """
    An AceTeam-specific node with field information for dynamic input/output types.
    """

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="AceTeamNode",
        display_name="AceTeam Node",
        version="0.4.0",
        parameter_type=Params,
    )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__.split("[")[0] != "AceTeamNode":
            assert cls not in aceteam_nodes
            aceteam_nodes.append(cls)

    @classmethod
    def type_info(cls) -> NodeTypeInfo:
        """Fixed information about the node and its properties."""
        raise NotImplementedError("Subclasses must implement this method")

    @cached_property
    def input_fields_info(self) -> Sequence[FieldInfo]:
        return ()

    @cached_property
    def output_fields_info(self) -> Sequence[FieldInfo]:
        return ()

    @cached_property
    def input_type(self) -> Type[Input_contra]:  # type: ignore
        return build_pydantic_model(self.input_fields_info)  # type: ignore

    @cached_property
    def output_type(self) -> Type[Output_co]:
        return build_pydantic_model(self.output_fields_info)  # type: ignore

    def parse_input(self, input: Mapping[str, Any]) -> DataMapping:
        return {
            field.name: field.python_type.model_validate(input[field.name])
            for field in self.input_fields_info
            if field.name in input
        }

    def parse_output(self, output: Mapping[str, Any]) -> DataMapping:
        return {
            field.name: field.python_type.model_validate(output[field.name])
            for field in self.output_fields_info
            if field.name in output
        }


aceteam_nodes: list[type[AceTeamNode]] = []


__all__ = [
    "AceTeamNode",
    "aceteam_nodes",
]
