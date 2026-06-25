"""Tests for XPathExtractNode."""

import pytest
from workflow_engine import StringValue, WorkflowEngine, WorkflowException
from workflow_engine.contexts import InMemoryExecutionContext
from workflow_engine.files import TextFileValue

from aceteam_nodes.nodes.xpath_extract import (
    XPathExtractInput,
    XPathExtractNode,
    XPathExtractOutput,
)


async def _run(
    engine: WorkflowEngine,
    context: InMemoryExecutionContext,
    xpath: str,
    html: str,
) -> list[str]:
    html_file = await StringValue(html).cast_to(TextFileValue, context=context)
    node = engine.create_node(
        XPathExtractNode,
        id="test",
        params=dict(xpath=xpath),
    )
    output = await node.run(
        context=context,
        input_type=XPathExtractInput,
        output_type=XPathExtractOutput,
        input=XPathExtractInput(html=html_file),
    )
    return [s.root for s in output.results.root]


async def test_extracts_element_text_content(
    engine: WorkflowEngine,
    context: InMemoryExecutionContext,
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
    context: InMemoryExecutionContext,
):
    html = '<ul><li><a href="/x">x</a></li><li><a href="/y">y</a></li></ul>'
    results = await _run(engine, context, "//a/@href", html)
    assert results == ["/x", "/y"]


async def test_xpath_text_predicate(
    engine: WorkflowEngine,
    context: InMemoryExecutionContext,
):
    """Use of XPath features that CSS cannot express: text-content matching."""
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
    context: InMemoryExecutionContext,
):
    results = await _run(engine, context, "//nonexistent", "<div><p>hi</p></div>")
    assert results == []


async def test_empty_html_returns_empty(
    engine: WorkflowEngine,
    context: InMemoryExecutionContext,
):
    results = await _run(engine, context, "//p", "")
    assert results == []


async def test_invalid_xpath_raises(
    engine: WorkflowEngine,
    context: InMemoryExecutionContext,
):
    with pytest.raises(WorkflowException, match="Invalid XPath"):
        await _run(engine, context, "//[bogus", "<div/>")


async def test_results_in_document_order(
    engine: WorkflowEngine,
    context: InMemoryExecutionContext,
):
    html = "<root><x>1</x><y><x>2</x></y><x>3</x></root>"
    results = await _run(engine, context, "//x", html)
    assert results == ["1", "2", "3"]
