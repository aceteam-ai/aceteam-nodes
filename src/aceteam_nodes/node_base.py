"""AceTeam node base class with auto-registration."""

from typing import Generic, TypeVar

from workflow_engine import Data, Node, Params
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo

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


aceteam_nodes: list[type[AceTeamNode]] = []


__all__ = [
    "AceTeamNode",
    "aceteam_nodes",
]
