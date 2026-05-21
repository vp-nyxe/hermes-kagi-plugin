"""Kagi-enriched search tool.

Returns the full Kagi v1 search response including enrichment data
(infoboxes, adjacent questions, interesting finds, related searches, etc.)
that the standard Hermes web_search contract discards.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _kagi_request(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST to the Kagi v1 API and return the parsed JSON response."""
    import httpx

    api_key = os.getenv("KAGI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "KAGI_API_KEY environment variable not set. "
            "Get your API key at https://kagi.com/api/keys"
        )

    url = f"https://kagi.com/api/v1/{endpoint.lstrip('/')}"
    logger.info("Kagi %s request to %s", endpoint, url)

    response = httpx.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _format_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single Kagi result to a clean dict."""
    item = {
        "title": result.get("title", ""),
        "url": result.get("url", ""),
        "snippet": result.get("snippet", ""),
    }
    if "time" in result:
        item["time"] = result["time"]
    if "image" in result and result["image"]:
        item["image_url"] = result["image"].get("url", "")
    # Include props when they exist (adjacent_question.question, infobox data, etc.)
    if "props" in result and result["props"]:
        item["props"] = result["props"]
    return item


def _extract_category(data: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    """Extract and format a result category from Kagi data."""
    return [_format_result(r) for r in data.get(key, [])]


KAGI_ENRICHED_SEARCH_SCHEMA: Dict[str, Any] = {
    "name": "kagi_enriched_search",
    "description": (
        "Perform a Kagi web search and return enriched results including "
        "infoboxes, adjacent questions, related searches, interesting finds, "
        "news, videos, images, and more. Uses the Kagi v1 API (requires KAGI_API_KEY)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to run.",
            },
            "workflow": {
                "type": "string",
                "description": (
                    "Type of results to return. Default is 'search' (web pages). "
                    "Other options: 'images', 'videos', 'news', 'podcasts'."
                ),
                "enum": ["search", "images", "videos", "news", "podcasts"],
                "default": "search",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (1-100).",
                "minimum": 1,
                "maximum": 100,
                "default": 10,
            },
            "include_enrichment": {
                "type": "boolean",
                "description": (
                    "Whether to include enrichment data (infoboxes, adjacent questions, "
                    "interesting finds, related searches, direct answers). Defaults to true."
                ),
                "default": True,
            },
        },
        "required": ["query"],
    },
}


def _handle_kagi_enriched_search(args: dict, **kw) -> str:
    from tools.registry import tool_result, tool_error

    query = str(args.get("query") or "").strip()
    if not query:
        return tool_error("query is required")

    workflow = str(args.get("workflow") or "search").strip().lower()
    limit = int(args.get("limit", 10))
    include_enrichment = bool(args.get("include_enrichment", True))

    if workflow not in {"search", "images", "videos", "news", "podcasts"}:
        workflow = "search"

    try:
        payload: Dict[str, Any] = {
            "query": query,
            "workflow": workflow,
            "limit": min(max(limit, 1), 100),
        }
        raw = _kagi_request("search", payload)
    except ValueError as exc:
        return tool_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Kagi enriched search error: %s", exc)
        return tool_error(f"Kagi enriched search failed: {exc}")

    data = raw.get("data", {})

    # Always include primary results
    result: Dict[str, Any] = {
        "success": True,
        "query": query,
        "workflow": workflow,
        "web_results": _extract_category(data, "search"),
    }

    # Workflow-specific categorized results
    if workflow == "images":
        result["images"] = _extract_category(data, "image")
    elif workflow == "videos":
        result["videos"] = _extract_category(data, "video")
    elif workflow == "news":
        result["news"] = _extract_category(data, "news")
    elif workflow == "podcasts":
        result["podcasts"] = _extract_category(data, "podcast")
        result["podcast_creators"] = _extract_category(data, "podcast_creator")

    if include_enrichment:
        # Knowledge panel / infobox summary
        infobox = _extract_category(data, "infobox")
        if infobox:
            result["infobox"] = infobox

        # Related questions (adjacent_question have props.question)
        adjacent = _extract_category(data, "adjacent_question")
        if adjacent:
            result["adjacent_questions"] = adjacent

        # Quick answers (math, conversions, etc.)
        direct = _extract_category(data, "direct_answer")
        if direct:
            result["direct_answers"] = direct

        # Related searches to refine the query
        related = _extract_category(data, "related_search")
        if related:
            result["related_searches"] = related

        # Small web / non-commercial interesting finds
        finds = _extract_category(data, "interesting_finds")
        if finds:
            result["interesting_finds"] = finds

        # Unique news from Kagi's news index
        interesting_news = _extract_category(data, "interesting_news")
        if interesting_news:
            result["interesting_news"] = interesting_news

        # Code repositories / resources
        code = _extract_category(data, "code")
        if code:
            result["code_results"] = code

        # Package tracking (if query was a tracking number)
        tracking = _extract_category(data, "package_tracking")
        if tracking:
            result["package_tracking"] = tracking

        # Weather (if query was weather-related)
        weather = _extract_category(data, "weather")
        if weather:
            result["weather"] = weather

        # Listicle-style results
        listicle = _extract_category(data, "listicle")
        if listicle:
            result["listicles"] = listicle

        # Web archive results
        archive = _extract_category(data, "web_archive")
        if archive:
            result["web_archive"] = archive

    # Also include categorized results for the primary workflow="search" case
    if workflow == "search":
        for category_key, result_key in (
            ("image", "images"),
            ("video", "videos"),
            ("news", "news"),
            ("podcast", "podcasts"),
        ):
            items = _extract_category(data, category_key)
            if items:
                result[result_key] = items

    return tool_result(result)
