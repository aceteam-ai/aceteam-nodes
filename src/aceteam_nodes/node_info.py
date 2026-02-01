"""Node type info for AceTeam nodes."""

from collections.abc import Sequence

from pydantic import BaseModel

from .field import FieldInfo


class NodeTypeInfo(BaseModel):
    """Represents a node type's metadata."""

    type: str
    display_name: str
    description: str
    params: Sequence[FieldInfo]


__all__ = [
    "NodeTypeInfo",
]
