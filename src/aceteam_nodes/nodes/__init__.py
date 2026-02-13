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

from workflow_engine import InputNode, Node, NodeRegistry, OutputNode
from workflow_engine.nodes import ForEachNode, IfElseNode, IfNode

from .api_call import APICallNode
from .comparison import (
    AndNode,
    EqualNode,
    GreaterThanEqualNode,
    GreaterThanNode,
    LessThanEqualNode,
    LessThanNode,
    NotEqualNode,
    NotNode,
    OrNode,
)
from .csv_reader import CSVReaderNode
from .data_transform import DataTransformNode
from .llm import LLMNode
from .text_io import TextInputNode

aceteam_node_registry = (
    NodeRegistry.builder()
    # system nodes
    .register_node_class(Node)
    .register_node_class(InputNode)
    .register_node_class(OutputNode)
    .register_node_class(ForEachNode)
    .register_node_class(IfNode)
    .register_node_class(IfElseNode)
    # our nodes
    .register_node_class(APICallNode)
    .register_node_class(AndNode)
    .register_node_class(CSVReaderNode)
    .register_node_class(DataTransformNode)
    .register_node_class(EqualNode)
    .register_node_class(GreaterThanNode)
    .register_node_class(GreaterThanEqualNode)
    .register_node_class(LessThanNode)
    .register_node_class(LessThanEqualNode)
    .register_node_class(LLMNode)
    .register_node_class(NotNode)
    .register_node_class(NotEqualNode)
    .register_node_class(OrNode)
    .register_node_class(TextInputNode)
).build()
