"""Browser Fetch node - authenticated web fetching via Playwright."""

import asyncio
import logging
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, ClassVar, Iterator, Literal, Type
from urllib.parse import urlparse

from overrides import override
from pydantic import Field
from workflow_engine import (
    Data,
    ExecutionContext,
    FloatValue,
    Node,
    NodeTypeInfo,
    Params,
    StringValue,
    WorkflowException,
)
from workflow_engine.core import StakeholderLevel

from ..playwright_profile import playwright_profile_context

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

# Scroll-settle: fixed cadence and DOM-quiet window (not configurable).
_SCROLL_TICK_S = 0.1
_SCROLL_DOM_QUIET_MS = 1_000

# Pixels from max scroll extent; larger means more document below (feed not fully scrolled).
_SCROLL_REMAINING_EPS_PX = 1.0
_SCROLL_MIN_SCROLL_RANGE_PX = 24  # Ignore tiny scrollbar hosts when gathering containers.
_SCROLL_MIN_CONTAINER_HEIGHT_PX = 32

# Long-lived HTTP (SSE, some XHR) may never fire requestfinished; ignore after this age.
_PENDING_REQUEST_MAX_AGE_S = 10.0

_SCROLL_GATHER_SCROLLABLES_JS = f"""
function __aceteamGatherScrollables() {{
  const out = [];
  const MIN_RANGE = {_SCROLL_MIN_SCROLL_RANGE_PX};
  const MIN_H = {_SCROLL_MIN_CONTAINER_HEIGHT_PX};
  const nodes = document.querySelectorAll('*');
  for (let i = 0; i < nodes.length; i++) {{
    const el = nodes[i];
    const cs = getComputedStyle(el);
    const oy = cs.overflowY;
    const canOverflow = oy === 'auto' || oy === 'scroll' || oy === 'overlay';
    const maxScroll = el.scrollHeight - el.clientHeight;
    if (!canOverflow || maxScroll < MIN_RANGE) continue;
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const rh = el.getBoundingClientRect();
    if (rh.height < MIN_H || rh.width < 16) continue;
    out.push(el);
  }}
  return out;
}}
"""

_SCROLL_BUMP_ALL_JS = f"""
() => {{
  {_SCROLL_GATHER_SCROLLABLES_JS}
  const epsProg = 1;
  const els = __aceteamGatherScrollables();
  const winBefore = window.scrollY;
  const before = els.map((e) => e.scrollTop);
  for (let i = 0; i < els.length; i++) {{
    const e = els[i];
    e.scrollTop += e.clientHeight;
  }}
  window.scrollBy(0, window.innerHeight);
  const winMoved = window.scrollY - winBefore > epsProg;
  let elMoved = false;
  for (let i = 0; i < els.length; i++) {{
    if (els[i].scrollTop - before[i] > epsProg) {{
      elMoved = true;
      break;
    }}
  }}
  return {{ anyProgress: winMoved || elMoved, nestedCount: els.length }};
}}
"""

_SCROLL_METRICS_ALL_JS = f"""
() => {{
  {_SCROLL_GATHER_SCROLLABLES_JS}
  const epsBottom = {_SCROLL_REMAINING_EPS_PX};
  const msQuiet = Date.now() - window.__aceteamLastDomChange;
  const se = document.documentElement;
  const winIH = window.innerHeight;
  const winMax = Math.max(0, se.scrollHeight - winIH);
  const winRem = winMax - window.scrollY;
  let allAtBottom = winRem <= epsBottom;
  let maxRemain = Math.max(winRem, 0);
  const els = __aceteamGatherScrollables();
  for (let i = 0; i < els.length; i++) {{
    const el = els[i];
    const maxY = Math.max(0, el.scrollHeight - el.clientHeight);
    const rem = maxY - el.scrollTop;
    maxRemain = Math.max(maxRemain, rem);
    if (rem > epsBottom) {{
      allAtBottom = false;
    }}
  }}
  return {{
    msQuiet,
    allAtBottom,
    nestedCount: els.length,
    windowRemainingBelow: Math.max(winRem, 0),
    maxRemainingBelow: maxRemain,
  }};
}}
"""


def _playwright_request_key(request: object) -> str:
    """Stable ID for a Playwright Request (same GUID as DevTools protocol object)."""
    impl = getattr(request, "_impl_obj", request)
    guid = getattr(impl, "_guid", None)
    if isinstance(guid, str):
        return guid
    return str(id(request))


class BrowserFetchParams(Params):
    url: StringValue = Field(
        title="URL",
        description="The URL to fetch.",
    )
    timeout: FloatValue = Field(
        title="Timeout",
        description="Navigation and wait timeout in seconds.",
        default=FloatValue(60.0),
    )


class BrowserFetchOutput(Data):
    html: StringValue = Field(
        title="HTML",
        description=(
            "Full document HTML after load, optional wait_for, and optional scroll-settle capture."
        ),
    )


class BrowserFetchNode(
    Node[
        Data,
        BrowserFetchOutput,
        BrowserFetchParams,
    ]
):
    """Fetches a page in a headless browser and returns its HTML for downstream use (e.g. LLM)."""

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        name="BrowserFetch",
        display_name="Browser Fetch",
        description=(
            "Loads a URL with Playwright and returns the rendered page HTML. Uses the shared "
            "Chromium profile from `aceteam-nodes browser-setup`. Optional scroll-settling "
            "nudges every sizable scroll container plus the window, then waits for quiescence "
            "(no scroll progress, all at bottom, short-request idle, DOM stable) before capture."
        ),
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
        url = self.params.url.root
        timeout_s = self.params.timeout.root

        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise WorkflowException(
                f"Invalid URL: {url!r}. Only http:// and https:// URLs are supported.",
                level=StakeholderLevel.USER,
            )

        try:
            async with playwright_profile_context() as browser_context:
                page = await browser_context.new_page()
                return await self._capture_html(
                    page=page,
                    url=url,
                    timeout_s=timeout_s,
                )
        except ImportError as e:
            raise WorkflowException(
                "Playwright is not installed. Install the 'playwright' extra "
                "(`uv sync --group playwright`) and run `playwright install chromium`.",
                level=StakeholderLevel.OPERATOR,
            ) from e

    @staticmethod
    @contextmanager
    def _page_inflight_counter(page: "Page") -> Iterator[Callable[[], int]]:
        """Track pending requests by Playwright request GUID; attach before goto.

        Count includes only requests whose start time is within `_PENDING_REQUEST_MAX_AGE_S`
        (monotonic clock). Older entries are purged so SSE / long polling do not block idle.
        """
        pending: dict[str, float] = {}

        def _purge_stale() -> None:
            cutoff = time.monotonic() - _PENDING_REQUEST_MAX_AGE_S
            for key in list(pending):
                if pending[key] < cutoff:
                    del pending[key]

        def _pending_short_count() -> int:
            _purge_stale()
            return len(pending)

        def _on_request(request: object) -> None:
            pending[_playwright_request_key(request)] = time.monotonic()

        def _on_finished(request: object) -> None:
            pending.pop(_playwright_request_key(request), None)

        page.on("request", _on_request)
        page.on("requestfinished", _on_finished)
        page.on("requestfailed", _on_finished)
        try:
            yield _pending_short_count
        finally:
            page.remove_listener("request", _on_request)
            page.remove_listener("requestfinished", _on_finished)
            page.remove_listener("requestfailed", _on_finished)

    async def _capture_html(
        self,
        *,
        page: "Page",
        url: str,
        timeout_s: float,
    ) -> BrowserFetchOutput:
        end_time = time.monotonic() + timeout_s
        page.set_default_timeout(timeout_s * 1_000.0)
        with self._page_inflight_counter(page) as get_inflight:
            try:
                await page.goto(url, wait_until="domcontentloaded")
            except Exception as e:
                raise WorkflowException(
                    f"Navigation to {url} failed: {e}",
                    level=StakeholderLevel.USER,
                ) from e
            await self._scroll_until_settled(
                page=page,
                end_time=end_time,
                get_inflight=get_inflight,
            )
        html = await page.content()
        return BrowserFetchOutput(html=StringValue(html))

    async def _scroll_until_settled(
        self,
        *,
        page: "Page",
        end_time: float,
        get_inflight: Callable[[], int],
    ) -> None:
        """
        Every tick: nudge every sizable overflow-y scroll container (and the window), sleep,
        then require quiescence—no scroll advancement on that nudge, every such scroller and the
        window at max extent, short-request network idle, plus 1s DOM quiet (or timeout).

        "Idle" ignores HTTP requests older than `_PENDING_REQUEST_MAX_AGE_S` (e.g. SSE).
        """

        await page.evaluate(
            """
            () => {
              if (window.__aceteamDomObserverInstalled) return;
              window.__aceteamLastDomChange = Date.now();
              const obs = new MutationObserver(() => {
                window.__aceteamLastDomChange = Date.now();
              });
              obs.observe(document.documentElement, {
                subtree: true,
                childList: true,
                attributes: true,
                characterData: true,
              });
              window.__aceteamDomObserverInstalled = true;
            }
            """
        )

        while True:
            now = time.monotonic()
            if now >= end_time:
                logger.debug(
                    "BrowserFetch scroll-settle: stopping (timeout; max duration reached "
                    "before this iteration)",
                )
                return

            bump = await page.evaluate(_SCROLL_BUMP_ALL_JS)
            any_progress = bool(bump["anyProgress"])
            nested_count = int(bump["nestedCount"])

            await asyncio.sleep(_SCROLL_TICK_S)

            m = await page.evaluate(_SCROLL_METRICS_ALL_JS)
            ms_quiet = float(m["msQuiet"])
            all_at_bottom = bool(m["allAtBottom"])
            win_rem = float(m["windowRemainingBelow"])
            max_rem = float(m["maxRemainingBelow"])
            nested_count_post = int(m["nestedCount"])
            inflight = get_inflight()
            net_ok = inflight == 0
            scroll_stuck = (not any_progress) and all_at_bottom
            dom_ok = ms_quiet >= _SCROLL_DOM_QUIET_MS

            conditions_ok = (
                ("scroll_stuck", scroll_stuck),
                ("network_idle", net_ok),
                ("dom_quiet", dom_ok),
            )
            met = [name for name, ok in conditions_ok if ok]
            not_met = [name for name, ok in conditions_ok if not ok]
            logger.debug(
                "BrowserFetch scroll-settle: iteration termination - met="
                f"{met}, not_met={not_met} "
                f"(any_progress={any_progress}, all_at_bottom={all_at_bottom}, "
                f"nested={nested_count}->{nested_count_post}, "
                f"win_rem_px={win_rem:.0f}, max_rem_px={max_rem:.0f}, "
                f"inflight_short<={_PENDING_REQUEST_MAX_AGE_S:.0f}s={inflight}, "
                f"ms_quiet={ms_quiet:.0f} / {_SCROLL_DOM_QUIET_MS}ms required)",
            )

            if scroll_stuck and net_ok and dom_ok:
                return


__all__ = [
    "BrowserFetchNode",
    "BrowserFetchOutput",
    "BrowserFetchParams",
]
