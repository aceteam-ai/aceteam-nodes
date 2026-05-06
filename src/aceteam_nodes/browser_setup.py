"""Interactive Playwright profile setup."""

import asyncio
import html
import json
import sys
from typing import Any

from .playwright_profile import playwright_profile_context, playwright_profile_dir


async def run_browser_setup() -> dict[str, Any]:
    profile_dir = playwright_profile_dir()
    profile_display = html.escape(str(profile_dir))

    try:
        async with playwright_profile_context(headless=False) as context:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.set_content(
                f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>AceTeam browser profile</title></head>
<body style="font:16px system-ui;padding:2rem;max-width:42rem;line-height:1.5">
  <h1 style="margin-top:0">AceTeam browser profile</h1>
  <p>Sign in to any sites you need. When you are done, <strong>close this browser
  window</strong> to save the profile for headless workflows.</p>
  <p style="color:#444">Profile directory:</p>
  <pre style="background:#f4f4f4;padding:0.75rem;overflow:auto"><code>{profile_display}</code></pre>
</body></html>"""
            )
            # Default wait_for_event timeout is 30s; interactive login often takes longer.
            await context.wait_for_event("close", timeout=0)
    except ImportError as e:
        return {
            "success": False,
            "error": (
                "Playwright is not installed. Install the playwright dependency group "
                "(`uv sync --group dev` or `uv sync --group playwright`) and run "
                "`playwright install chromium`."
            ),
            "detail": str(e),
        }

    return {
        "success": True,
        "profile": str(profile_dir),
        "message": "Browser profile saved. Headless runs use this directory.",
    }


def main() -> None:
    """Launch Chromium with the shared Ace profile; close the window to save."""
    try:
        result = asyncio.run(run_browser_setup())
        print(json.dumps(result, indent=2, default=str))
        if not result.get("success", True):
            sys.exit(1)
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        sys.exit(1)
