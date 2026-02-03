"""Tests for individual nodes."""

import pytest
from workflow_engine import BooleanValue, FloatValue, StringValue
from workflow_engine.contexts.in_memory import InMemoryContext

from aceteam_nodes.nodes.comparison import (
    AndNode,
    ComparisonInput,
    ComparisonParams,
    EqualNode,
    GreaterThanNode,
    LessThanNode,
    LogicalInput,
    LogicalParams,
    NotInput,
    NotNode,
    OrNode,
)
from aceteam_nodes.nodes.csv_reader import CSVReaderNode, CSVReaderNodeParams
from aceteam_nodes.nodes.data_transform import (
    DataTransformNode,
    DataTransformNodeInput,
    DataTransformNodeParams,
)
from aceteam_nodes.nodes.text_io import TextInputNode, TextInputNodeParams


@pytest.fixture
def context():
    return InMemoryContext()


async def test_text_input_node(context):
    node = TextInputNode(
        id="test",
        params=TextInputNodeParams(text=StringValue("Hello World")),
    )
    output = await node.run(context, None)
    assert output.output.root == "Hello World"


async def test_data_transform_passthrough(context):
    node = DataTransformNode(
        id="test",
        params=DataTransformNodeParams(instruction=StringValue("Pass through")),
    )
    input_data = DataTransformNodeInput(input=StringValue("test data"))
    output = await node.run(context, input_data)
    assert output.output.root == "test data"


async def test_csv_reader_node(context):
    node = CSVReaderNode(
        id="test",
        params=CSVReaderNodeParams(sample_data=StringValue("name,age\nAlice,30\nBob,25")),
    )
    output = await node.run(context, None)
    assert "Alice" in output.data.root
    assert "Bob" in output.data.root


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
    node = AndNode(id="test", params=LogicalParams())
    result = await node.run(context, LogicalInput(a=BooleanValue(True), b=BooleanValue(True)))
    assert result.result.root is True

    result = await node.run(context, LogicalInput(a=BooleanValue(True), b=BooleanValue(False)))
    assert result.result.root is False


async def test_or_node(context):
    node = OrNode(id="test", params=LogicalParams())
    result = await node.run(context, LogicalInput(a=BooleanValue(False), b=BooleanValue(True)))
    assert result.result.root is True

    result = await node.run(context, LogicalInput(a=BooleanValue(False), b=BooleanValue(False)))
    assert result.result.root is False


async def test_not_node(context):
    node = NotNode(id="test", params=LogicalParams())
    result = await node.run(context, NotInput(a=BooleanValue(True)))
    assert result.result.root is False

    result = await node.run(context, NotInput(a=BooleanValue(False)))
    assert result.result.root is True
