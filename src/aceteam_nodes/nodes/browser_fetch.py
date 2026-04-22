"""Browser Fetch node - authenticated web fetching via Playwright."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar, Literal, Type
from urllib.parse import urlparse

from overrides import override
from pydantic import Field
from workflow_engine import (
    BooleanValue,
    Data,
    DataValue,
    ExecutionContext,
    FloatValue,
    IntegerValue,
    JSONValue,
    Node,
    NodeTypeInfo,
    Params,
    SequenceValue,
    StringMapValue,
    StringValue,
    WorkflowException,
)
from workflow_engine.core import StakeholderLevel

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class ExtractRule(Data):
    name: StringValue = Field(
        title="Name",
        description="Key under which the extracted value is returned.",
    )
    selector: StringValue = Field(
        title="Selector",
        description="CSS selector to match.",
    )
    attr: StringValue = Field(
        title="Attribute",
        description=(
            "Attribute to extract. Empty string extracts inner text; "
            "'html' extracts innerHTML; any other value extracts that attribute."
        ),
        default=StringValue(""),
    )
    multiple: BooleanValue = Field(
        title="Multiple",
        description="If true, return all matches as a list; otherwise return the first match.",
        default=BooleanValue(False),
    )


class BrowserFetchParams(Params):
    url: StringValue = Field(
        title="URL",
        description="The URL to fetch.",
    )
    cookies: StringMapValue[StringValue] = Field(
        title="Cookies",
        description="Cookies to send with the request, as a name -> value map.",
        default=StringMapValue({}),
    )
    headers: StringMapValue[StringValue] = Field(
        title="Headers",
        description="Extra HTTP headers to send (e.g., User-Agent, Authorization).",
        default=StringMapValue({}),
    )
    wait_for: StringValue = Field(
        title="Wait For",
        description="CSS selector to wait for before extraction. Empty string disables waiting.",
        default=StringValue(""),
    )
    extract: SequenceValue[DataValue[ExtractRule]] = Field(
        title="Extract",
        description="Extraction rules applied against the rendered DOM.",
        default=SequenceValue[DataValue[ExtractRule]]([]),
    )
    render_js: BooleanValue = Field(
        title="Render JS",
        description="If false, disables JavaScript in the browser context.",
        default=BooleanValue(True),
    )
    include_html: BooleanValue = Field(
        title="Include HTML",
        description="If true, include the full page HTML in the output.",
        default=BooleanValue(False),
    )
    timeout: FloatValue = Field(
        title="Timeout",
        description="Navigation and wait timeout in seconds.",
        default=FloatValue(30.0),
    )


class BrowserFetchOutput(Data):
    status: IntegerValue = Field(
        title="Status",
        description="HTTP status code of the main navigation response.",
    )
    extracted: StringMapValue[JSONValue] = Field(
        title="Extracted",
        description="Extracted values keyed by the rule's name.",
    )
    html: StringValue = Field(
        title="HTML",
        description="Full page HTML. Empty unless include_html=true.",
    )


class BrowserFetchNode(
    Node[
        Data,
        BrowserFetchOutput,
        BrowserFetchParams,
    ]
):
    """Fetches a web page via Playwright, optionally rendering JS and extracting values."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        name="BrowserFetch",
        display_name="Browser Fetch",
        description="Fetches a web page via a headless browser and extracts values by selector.",
        version="0.1.0",
        parameter_type=BrowserFetchParams,
    )

    type: Literal["BrowserFetch"] = "BrowserFetch"  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    @override
    def static_input_type(cls) -> Type[Data]:
        return Data

    @classmethod
    @override
    def static_output_type(cls) -> Type[BrowserFetchOutput]:
        return BrowserFetchOutput

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[Data],
        output_type: Type[BrowserFetchOutput],
        input: Data,
    ) -> BrowserFetchOutput:
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise WorkflowException(
                "Playwright is not installed. Install the 'playwright' extra "
                "(`uv sync --group playwright`) and run `playwright install chromium`.",
                level=StakeholderLevel.USER,
            ) from e

        url = self.params.url.root
        timeout_ms = int(self.params.timeout.root * 1000)
        headers = {k: v.root for k, v in self.params.headers.items()}
        wait_for = self.params.wait_for.root
        render_js = self.params.render_js.root
        include_html = self.params.include_html.root

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise WorkflowException(
                f"Invalid URL: {url!r}",
                level=StakeholderLevel.USER,
            )
        cookie_domain = parsed.hostname or ""
        cookies_payload = [
            {"name": name, "value": value.root, "domain": cookie_domain, "path": "/"}
            for name, value in self.params.cookies.items()
        ]

        logger.info(f"BrowserFetch navigating to {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                browser_context = await browser.new_context(
                    java_script_enabled=render_js,
                    extra_http_headers=headers or None,
                )
                if cookies_payload:
                    await browser_context.add_cookies(cookies_payload)  # type: ignore[arg-type]

                page = await browser_context.new_page()
                page.set_default_timeout(timeout_ms)

                try:
                    response = await page.goto(url, wait_until="load")
                except Exception as e:
                    raise WorkflowException(
                        f"Navigation to {url} failed: {e}",
                        level=StakeholderLevel.USER,
                    ) from e

                if wait_for:
                    try:
                        await page.wait_for_selector(wait_for, timeout=timeout_ms)
                    except Exception as e:
                        raise WorkflowException(
                            f"Timed out waiting for selector {wait_for!r}: {e}",
                            level=StakeholderLevel.USER,
                        ) from e

                status = response.status if response is not None else 0
                extracted = await self._run_extractions(page)
                html = await page.content() if include_html else ""
            finally:
                await browser.close()

        return BrowserFetchOutput(
            status=IntegerValue(status),
            extracted=StringMapValue[JSONValue](
                {name: JSONValue(value) for name, value in extracted.items()}
            ),
            html=StringValue(html),
        )

    async def _run_extractions(self, page: Page) -> dict[str, str | list[str]]:
        results: dict[str, str | list[str]] = {}
        for rule_value in self.params.extract:
            rule = rule_value.root
            name = rule.name.root
            selector = rule.selector.root
            attr = rule.attr.root
            multiple = rule.multiple.root

            if multiple:
                elements = await page.query_selector_all(selector)
                results[name] = [await self._extract_one(el, attr) for el in elements]
            else:
                element = await page.query_selector(selector)
                results[name] = await self._extract_one(element, attr) if element else ""
        return results

    @staticmethod
    async def _extract_one(element, attr: str) -> str:
        if element is None:
            return ""
        if attr == "":
            text = await element.inner_text()
            return text or ""
        if attr == "html":
            html = await element.inner_html()
            return html or ""
        value = await element.get_attribute(attr)
        return value or ""


__all__ = [
    "BrowserFetchNode",
    "BrowserFetchOutput",
    "BrowserFetchParams",
    "ExtractRule",
]
