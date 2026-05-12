"""Community node discovery via Python entry_points."""

from __future__ import annotations

import logging
from importlib.metadata import entry_points

from workflow_engine import NodeRegistry

from .nodes import aceteam_node_registry

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "aceteam.nodes"


def discover_community_nodes(builder) -> list[str]:
    """
    Scan installed packages for aceteam.nodes entry points and register their nodes.

    Each entry point must be a callable with signature:
        register_nodes(builder: EagerNodeRegistryBuilder) -> None

    Returns a list of successfully loaded package names.
    """
    loaded = []
    eps = entry_points(group=ENTRY_POINT_GROUP)

    for ep in eps:
        try:
            register_fn = ep.load()
            register_fn(builder)
            loaded.append(ep.name)
            logger.info("Loaded community nodes from %s", ep.name)
        except Exception:
            logger.warning("Failed to load community nodes from %s", ep.name, exc_info=True)

    return loaded


def build_full_registry() -> NodeRegistry:
    """
    Build a registry containing core aceteam nodes plus any installed community nodes.

    Uses NodeRegistry.extend() to start from the existing aceteam_node_registry,
    then discovers and registers community nodes via entry_points.
    """
    builder = aceteam_node_registry.extend(lazy=False)
    loaded = discover_community_nodes(builder)
    if loaded:
        logger.info("Community node packages loaded: %s", ", ".join(loaded))
    return builder.build()


__all__ = [
    "ENTRY_POINT_GROUP",
    "build_full_registry",
    "discover_community_nodes",
]
