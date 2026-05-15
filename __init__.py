"""Kagi web search + extract + enriched search plugin.

Registers the Kagi WebSearchProvider (search/extract) and a bonus
``kagi_enriched_search`` tool that exposes all Kagi v1 enrichment data
(infoboxes, adjacent questions, interesting finds, related searches, etc.)
that the standard Hermes search contract strips out.
"""

from __future__ import annotations

import os


def _check_kagi_available() -> bool:
    """Return True when KAGI_API_KEY is set."""
    return bool(os.getenv("KAGI_API_KEY", "").strip())


def register(ctx) -> None:
    """Register the Kagi provider and enriched-search tool."""
    # Lazy imports so the sibling modules have been set up by
    # importlib when __init__.py exec_module runs them.
    from hermes_plugins.web_kagi.provider import KagiWebSearchProvider
    from hermes_plugins.web_kagi.tools import (
        KAGI_ENRICHED_SEARCH_SCHEMA,
        _handle_kagi_enriched_search,
    )

    ctx.register_web_search_provider(KagiWebSearchProvider())

    ctx.register_tool(
        name="kagi_enriched_search",
        toolset="web",
        schema=KAGI_ENRICHED_SEARCH_SCHEMA,
        handler=_handle_kagi_enriched_search,
        check_fn=_check_kagi_available,
        emoji="🔎",
    )
