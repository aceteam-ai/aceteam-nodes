"""Tests for XPathExtractNode."""

import pytest
from workflow_engine import StringValue, WorkflowException
from workflow_engine.contexts.in_memory import InMemoryExecutionContext
from workflow_engine.files import TextFileValue

from aceteam_nodes.nodes.xpath_extract import (
    XPathExtractInput,
    XPathExtractNode,
    XPathExtractParams,
)


@pytest.fixture
def context():
    return InMemoryExecutionContext()


async def _run(context, xpath: str, html: str) -> list[str]:
    html_file = await StringValue(html).cast_to(TextFileValue, context=context)
    node = XPathExtractNode(
        id="test",
        params=XPathExtractParams(xpath=StringValue(xpath)),
    )
    output = await node.run(
        context=context,
        input_type=node.static_input_type(),
        output_type=node.static_output_type(),
        input=XPathExtractInput(html=html_file),
    )
    return [s.root for s in output.results.root]


async def test_extracts_element_text_content(context):
    html = """
    <html><body>
      <article><h2><a href="/a">First headline</a></h2></article>
      <article><h2><a href="/b">Second <span>nested</span> headline</a></h2></article>
    </body></html>
    """
    results = await _run(context, "//article//h2//a", html)
    assert results == ["First headline", "Second nested headline"]


async def test_extracts_attributes(context):
    html = '<ul><li><a href="/x">x</a></li><li><a href="/y">y</a></li></ul>'
    results = await _run(context, "//a/@href", html)
    assert results == ["/x", "/y"]


async def test_xpath_text_predicate(context):
    """Use of XPath features that CSS cannot express: text-content matching."""
    html = """
    <div>
      <p>Posted by Alice</p>
      <p>Random other content</p>
      <p>Posted by Bob</p>
    </div>
    """
    results = await _run(context, '//p[contains(., "Posted by")]', html)
    assert results == ["Posted by Alice", "Posted by Bob"]


async def test_no_matches_returns_empty(context):
    results = await _run(context, "//nonexistent", "<div><p>hi</p></div>")
    assert results == []


async def test_empty_html_returns_empty(context):
    results = await _run(context, "//p", "")
    assert results == []


async def test_invalid_xpath_raises(context):
    with pytest.raises(WorkflowException, match="Invalid XPath"):
        await _run(context, "//[bogus", "<div/>")


async def test_results_in_document_order(context):
    html = "<root><x>1</x><y><x>2</x></y><x>3</x></root>"
    results = await _run(context, "//x", html)
    assert results == ["1", "2", "3"]
