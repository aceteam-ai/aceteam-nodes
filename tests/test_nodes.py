"""Tests for individual nodes."""

import pytest
from workflow_engine import BooleanValue, Empty, FloatValue
from workflow_engine.contexts.in_memory import InMemoryContext

from aceteam_nodes.nodes.comparison import (
    AndNode,
    ComparisonInput,
    ComparisonParams,
    EqualNode,
    GreaterThanNode,
    LessThanNode,
    LogicalInput,
    NotInput,
    NotNode,
    OrNode,
)


@pytest.fixture
def context():
    return InMemoryContext()


async def test_equal_node(context):
    node = EqualNode(id="test", params=ComparisonParams())
    result = await node.run(context, ComparisonInput(a=FloatValue(5.0), b=FloatValue(5.0)))
    assert result.result.root is True

    result = await node.run(context, ComparisonInput(a=FloatValue(5.0), b=FloatValue(3.0)))
    assert result.result.root is False


async def test_greater_than_node(context):
    node = GreaterThanNode(id="test", params=ComparisonParams())
    result = await node.run(context, ComparisonInput(a=FloatValue(5.0), b=FloatValue(3.0)))
    assert result.result.root is True

    result = await node.run(context, ComparisonInput(a=FloatValue(3.0), b=FloatValue(5.0)))
    assert result.result.root is False


async def test_less_than_node(context):
    node = LessThanNode(id="test", params=ComparisonParams())
    result = await node.run(context, ComparisonInput(a=FloatValue(3.0), b=FloatValue(5.0)))
    assert result.result.root is True


async def test_and_node(context):
    node = AndNode(id="test", params=Empty())
    result = await node.run(context, LogicalInput(a=BooleanValue(True), b=BooleanValue(True)))
    assert result.result.root is True

    result = await node.run(context, LogicalInput(a=BooleanValue(True), b=BooleanValue(False)))
    assert result.result.root is False


async def test_or_node(context):
    node = OrNode(id="test", params=Empty())
    result = await node.run(context, LogicalInput(a=BooleanValue(False), b=BooleanValue(True)))
    assert result.result.root is True

    result = await node.run(context, LogicalInput(a=BooleanValue(False), b=BooleanValue(False)))
    assert result.result.root is False


async def test_not_node(context):
    node = NotNode(id="test", params=Empty())
    result = await node.run(context, NotInput(a=BooleanValue(True)))
    assert result.result.root is False

    result = await node.run(context, NotInput(a=BooleanValue(False)))
    assert result.result.root is True
