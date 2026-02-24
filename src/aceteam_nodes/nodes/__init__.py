"""AceTeam workflow nodes."""

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
from .llm import LLMNode

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
    .register_node_class(EqualNode)
    .register_node_class(GreaterThanNode)
    .register_node_class(GreaterThanEqualNode)
    .register_node_class(LessThanNode)
    .register_node_class(LessThanEqualNode)
    .register_node_class(LLMNode)
    .register_node_class(NotNode)
    .register_node_class(NotEqualNode)
    .register_node_class(OrNode)
).build()
