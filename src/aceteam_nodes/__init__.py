"""AceTeam workflow nodes for local execution.

This package is a repository of independently-installable nodes. Each node's
dependencies are gated behind its own optional extra, so nodes must be
imported from their leaf modules (e.g. ``aceteam_nodes.nodes.api_call``),
never re-exported from package ``__init__`` files. The entry points in
``pyproject.toml`` are the canonical map of node names to modules.
"""

__version__ = "0.8.0"
