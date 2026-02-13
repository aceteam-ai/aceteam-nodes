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
    .register_base_node_class(Node)
    .register_node_class("Input", InputNode)
    .register_node_class("Output", OutputNode)
    .register_node_class("ForEach", ForEachNode)
    .register_node_class("If", IfNode)
    .register_node_class("IfElse", IfElseNode)
    # our nodes
    .register_node_class("APICall", APICallNode)
    .register_node_class("And", AndNode)
    .register_node_class("CSVReader", CSVReaderNode)
    .register_node_class("DataTransform", DataTransformNode)
    .register_node_class("Equal", EqualNode)
    .register_node_class("GreaterThan", GreaterThanNode)
    .register_node_class("GreaterThanEqual", GreaterThanEqualNode)
    .register_node_class("LessThan", LessThanNode)
    .register_node_class("LessThanEqual", LessThanEqualNode)
    .register_node_class("LLM", LLMNode)
    .register_node_class("Not", NotNode)
    .register_node_class("NotEqual", NotEqualNode)
    .register_node_class("Or", OrNode)
    .register_node_class("TextInput", TextInputNode)
).build()
