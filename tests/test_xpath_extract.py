"""Tests for XPathExtractNode."""

from workflow_engine import (
    ExecutionContext,
    SequenceValue,
    StringValue,
    WorkflowEngine,
    WorkflowExecutionResultStatus,
)
from workflow_engine.files import TextFileValue

from aceteam_nodes.nodes.xpath_extract import XPathExtractNode
from tests.workflow_helpers import error_messages, execute_single_node

_INPUT_FIELDS = {"html": TextFileValue}
_OUTPUT_FIELDS = {"results": SequenceValue[StringValue]}


async def _run(
    engine: WorkflowEngine,
    context: ExecutionContext,
    xpath: str,
    html: str,
) -> list[str]:
    html_file = await StringValue(html).cast_to(TextFileValue, context=context)
    result = await execute_single_node(
        engine,
        context,
        XPathExtractNode,
        params={"xpath": xpath},
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"html": html_file},
    )
    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    return [s.root for s in result.output["results"].root]


async def test_extracts_element_text_content(
    engine: WorkflowEngine,
    context: ExecutionContext,
):
    html = """
    <html><body>
      <article><h2><a href="/a">First headline</a></h2></article>
      <article><h2><a href="/b">Second <span>nested</span> headline</a></h2></article>
    </body></html>
    """
    results = await _run(engine, context, "//article//h2//a", html)
    assert results == ["First headline", "Second nested headline"]


async def test_extracts_attributes(
    engine: WorkflowEngine,
    context: ExecutionContext,
):
    html = '<ul><li><a href="/x">x</a></li><li><a href="/y">y</a></li></ul>'
    results = await _run(engine, context, "//a/@href", html)
    assert results == ["/x", "/y"]


async def test_xpath_text_predicate(
    engine: WorkflowEngine,
    context: ExecutionContext,
):
    html = """
    <div>
      <p>Posted by Alice</p>
      <p>Random other content</p>
      <p>Posted by Bob</p>
    </div>
    """
    results = await _run(engine, context, '//p[contains(., "Posted by")]', html)
    assert results == ["Posted by Alice", "Posted by Bob"]


async def test_no_matches_returns_empty(
    engine: WorkflowEngine,
    context: ExecutionContext,
):
    results = await _run(engine, context, "//nonexistent", "<div><p>hi</p></div>")
    assert results == []


async def test_empty_html_returns_empty(
    engine: WorkflowEngine,
    context: ExecutionContext,
):
    results = await _run(engine, context, "//p", "")
    assert results == []


async def test_invalid_xpath_raises(
    engine: WorkflowEngine,
    context: ExecutionContext,
):
    html_file = await StringValue("<div/>").cast_to(TextFileValue, context=context)
    result = await execute_single_node(
        engine,
        context,
        XPathExtractNode,
        params={"xpath": "//[bogus"},
        input_fields=_INPUT_FIELDS,
        output_fields=_OUTPUT_FIELDS,
        input={"html": html_file},
    )
    assert result.status is WorkflowExecutionResultStatus.ERROR
    assert any("Invalid XPath" in message for message in error_messages(result))


async def test_results_in_document_order(
    engine: WorkflowEngine,
    context: ExecutionContext,
):
    html = "<root><x>1</x><y><x>2</x></y><x>3</x></root>"
    results = await _run(engine, context, "//x", html)
    assert results == ["1", "2", "3"]
