"""XPath Extract node - extract a sequence of texts from an HTML document."""

from typing import ClassVar, Type

from lxml import html as lxml_html
from overrides import override
from pydantic import Field
from workflow_engine import (
    Data,
    ExecutionContext,
    Node,
    NodeTypeInfo,
    Params,
    SequenceValue,
    StakeholderLevel,
    StringValue,
    WorkflowException,
)
from workflow_engine.files import TextFileValue


class XPathExtractParams(Params):
    xpath: StringValue = Field(
        title="XPath",
        description=(
            "XPath 1.0 expression evaluated against the parsed HTML. May target elements "
            "(text content is extracted), attributes (e.g. `//a/@href`), or text nodes "
            "(e.g. `//h2/text()`)."
        ),
    )


class XPathExtractInput(Data):
    html: TextFileValue = Field(
        title="HTML",
        description="The HTML document to parse.",
    )


class XPathExtractOutput(Data):
    results: SequenceValue[StringValue] = Field(
        title="Results",
        description="Extracted strings, one per XPath match, in document order.",
    )


class XPathExtractNode(
    Node[
        XPathExtractInput,
        XPathExtractOutput,
        XPathExtractParams,
    ]
):
    """Parse HTML and extract a sequence of strings via an XPath expression."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="XPath Extract",
        description=(
            "Parses HTML with lxml and evaluates an XPath 1.0 expression. Element matches "
            "are reduced to their text content; attribute and text-node matches are returned "
            "as-is. Results are returned in document order."
        ),
        version="0.1.0",
        parameter_type=XPathExtractParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[XPathExtractInput]:
        return XPathExtractInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[XPathExtractOutput]:
        return XPathExtractOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[XPathExtractInput],
        output_type: Type[XPathExtractOutput],
        input: XPathExtractInput,
    ) -> XPathExtractOutput:
        xpath = self.params.xpath.root
        html = await input.html.read_text(context)

        try:
            tree = lxml_html.fromstring(html) if html.strip() else None
        except lxml_html.etree.ParserError as e:
            raise WorkflowException(
                f"Failed to parse HTML: {e}",
                level=StakeholderLevel.USER,
            ) from e

        if tree is None:
            return XPathExtractOutput(results=SequenceValue[StringValue]([]))

        try:
            matches = tree.xpath(xpath)
        except lxml_html.etree.XPathEvalError as e:
            raise WorkflowException(
                f"Invalid XPath expression {xpath!r}: {e}",
                level=StakeholderLevel.USER,
            ) from e

        if not isinstance(matches, list):
            # XPath expressions like `count(...)` return a scalar; coerce to single-item list.
            matches = [matches]

        results: list[StringValue] = []
        for m in matches:
            if isinstance(m, str):
                text = m
            elif hasattr(m, "text_content"):
                text = m.text_content()
            else:
                text = str(m)
            results.append(StringValue(text))

        return XPathExtractOutput(results=SequenceValue[StringValue](results))


__all__ = [
    "XPathExtractInput",
    "XPathExtractNode",
    "XPathExtractOutput",
    "XPathExtractParams",
]
