"""Shared Chromium user-data for all Playwright usage in aceteam-nodes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

from platformdirs import user_data_dir

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page


def playwright_profile_dir() -> Path:
    """
    Directory persisted across `browser-setup` and BrowserFetch.
    """
    base = Path(user_data_dir("aceteam-nodes", "AceTeam"))
    path = base / "playwright-chromium-profile"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def _install_strip_headless_chrome_user_agent(context: "BrowserContext") -> None:
    """
    CDP `Network.setUserAgentOverride` so `HeadlessChrome` is not sent on the wire.

    Stealth only spoofs `navigator.*` via init scripts; HTTP requests still used `HeadlessChrome`
    until we override at the network layer (some CDNs respond with `ERR_HTTP2_PROTOCOL_ERROR`).
    Wrap ``new_page`` so every tab gets the override before its first navigation.
    """
    user_agent: str | None = None

    async def apply(page: "Page") -> None:
        nonlocal user_agent
        if user_agent is None:
            raw = await page.evaluate("navigator.userAgent")
            if not isinstance(raw, str):
                raise ValueError(f"User agent is not a string, got {type(raw).__name__} instead.")
            user_agent = raw.replace("HeadlessChrome", "Chrome")
        session = await page.context.new_cdp_session(page)
        await session.send("Network.enable", {})
        await session.send(
            "Network.setUserAgentOverride",
            {"userAgent": user_agent},
        )

    for existing in context.pages:
        await apply(existing)

    orig_new_page: Any = context.new_page

    async def new_page_with_ua(*args: Any, **kwargs: Any) -> Any:
        page = await orig_new_page(*args, **kwargs)
        await apply(page)
        return page

    context.new_page = new_page_with_ua  # type: ignore[method-assign]


@asynccontextmanager
async def playwright_profile_context(
    *,
    headless: bool = True,
) -> AsyncIterator[BrowserContext]:
    """
    Launch Chromium with the shared persistent profile and yield its ``BrowserContext``.

    Stealth + persistent profile details are spelled out inline below (why ``use_async``, why
    ``apply_stealth_async``, why ``--accept-lang``, CDP UA).

    Closes the context on exit; if the user already closed the browser (e.g. during
    ``browser-setup``), closing again is best-effort.
    """
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth

    stealth = Stealth()
    # launch_persistent_context is still unhooked (upstream TODO in playwright-stealth),
    # so the rest below is required.
    async with stealth.use_async(async_playwright()) as p:
        browser_context = await p.chromium.launch_persistent_context(
            str(playwright_profile_dir()),
            channel="chromium",
            headless=headless,
            java_script_enabled=True,
            # Persistent launch never receives stealth's hooked chromium.launch() CLI merge.
            # Keep --accept-lang so Accept-Language matches stealth's navigator_languages scripts.
            args=[
                f"--accept-lang={','.join(stealth.navigator_languages_override)}",
            ],
        )
        # JS evasions (`navigator.webdriver`, plugins, etc.)
        # does not change outbound HTTP User-Agent
        await stealth.apply_stealth_async(browser_context)
        await _install_strip_headless_chrome_user_agent(browser_context)
        try:
            yield browser_context
        finally:
            with suppress(Exception):
                await browser_context.close()


__all__ = [
    "playwright_profile_context",
    "playwright_profile_dir",
]
