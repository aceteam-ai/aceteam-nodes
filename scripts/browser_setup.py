#!/usr/bin/env python3
"""Standalone browser profile setup (same as the installed console scripts).

From the repo: ``uv run python scripts/browser_setup.py``

Requires the Playwright optional group: ``uv sync --group playwright`` and
``playwright install chromium``.
"""

from aceteam_nodes.browser_setup import main

if __name__ == "__main__":
    main()
