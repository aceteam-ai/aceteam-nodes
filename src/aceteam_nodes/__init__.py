"""AceTeam workflow nodes for local execution."""

__version__ = "0.1.2"

from .node_base import AceTeamNode, aceteam_nodes


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
    "aceteam_nodes",
]
