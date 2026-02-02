"""AceTeam workflow nodes for local execution."""

__version__ = "0.1.1"

from .field import FieldInfo, FieldType
from .node_base import AceTeamNode, aceteam_nodes
from .node_info import NodeTypeInfo
from .workflow import AceTeamWorkflow


def __getattr__(name: str):
    """Lazy imports for modules that require optional dependencies (litellm)."""
    if name == "CLIContext":
        from .context import CLIContext

        return CLIContext
    if name == "run_workflow_from_file":
        from .execution import run_workflow_from_file

        return run_workflow_from_file
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AceTeamNode",
    "AceTeamWorkflow",
    "CLIContext",
    "FieldInfo",
    "FieldType",
    "NodeTypeInfo",
    "aceteam_nodes",
    "run_workflow_from_file",
]
