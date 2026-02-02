"""AceTeam workflow nodes.

Node submodules are NOT auto-imported here to avoid registration conflicts
when this package is used as a library alongside a platform that defines
its own versions of some nodes (e.g., APICallNode, LLMNode).

Import specific node modules directly:
    from aceteam_nodes.nodes.comparison import EqualNode
    from aceteam_nodes.nodes.conditional import IfNode

Or call register_all_nodes() to trigger auto-registration of all nodes
(e.g., before deserializing a workflow file).
"""


def register_all_nodes():
    """Import all node modules to trigger auto-registration in workflow_engine."""
    from . import api_call as _  # noqa: F401
    from . import comparison as _  # noqa: F811, F401
    from . import conditional as _  # noqa: F811, F401
    from . import csv_reader as _  # noqa: F811, F401
    from . import data_transform as _  # noqa: F811, F401
    from . import iteration as _  # noqa: F811, F401
    from . import llm as _  # noqa: F811, F401
    from . import text_io as _  # noqa: F811, F401
