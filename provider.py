"""Kagi web search + extract provider — bundled, auto-loaded.

Uses the Kagi v1 API (https://kagi.com/api/v1). Requires a Kagi
API key with v1 access; keys are scoped to api.kagi.com but the
endpoint is https://kagi.com/api/v1.

Capabilities:
- ``supports_search()``  -> True (Kagi ``/search``)
- ``supports_extract()`` -> True (Kagi ``/extract``)
- ``supports_crawl()``   -> False

Config keys this provider responds to::

    web:
      search_backend: "kagi"
      extract_backend: "kagi"
      backend: "kagi"

Env vars::

    KAGI_API_KEY=...   # https://kagi.com/api/keys (required)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from agent.web_search_provider import WebSearchProvider

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


def _normalize_kagi_search_results(response: Dict[str, Any]) -> Dict[str, Any]:
    """Map Kagi ``/search`` response to ``{success, data: {web: [...]}}``."""
    web_results = []
    data = response.get("data", {})

    # Primary web results
    for i, result in enumerate(data.get("search", [])):
        web_results.append(
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "description": result.get("snippet", ""),
                "position": i + 1,
            }
        )

    # Fall back to news results when no web results exist
    if not web_results:
        for i, result in enumerate(data.get("news", [])):
            web_results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("snippet", ""),
                    "position": i + 1,
                }
            )

    # Last resort — any other result category
    if not web_results:
        for category in ("video", "podcast", "interesting_finds", "code"):
            for i, result in enumerate(data.get(category, [])):
                web_results.append(
                    {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "description": result.get("snippet", ""),
                        "position": i + 1,
                    }
                )
            if web_results:
                break

    return {"success": True, "data": {"web": web_results}}


def _normalize_kagi_extract(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map Kagi ``/extract`` response to standard documents."""
    documents: List[Dict[str, Any]] = []
    data = response.get("data", [])

    errors = response.get("errors", [])
    error_by_url = {}
    for err in errors:
        error_by_url[err.get("url", "")] = err.get("message", "extraction failed")

    for item in data:
        url = item.get("url", "")
        raw = item.get("markdown", "") or ""
        documents.append(
            {
                "url": url,
                "title": os.path.basename(url.rstrip("/")).replace("-", " ").replace("_", " ").title() or url,
                "content": raw,
                "raw_content": raw,
                "metadata": {"sourceURL": url},
            }
        )

    return documents


class KagiWebSearchProvider(WebSearchProvider):
    """Kagi search + extract provider."""

    @property
    def name(self) -> str:
        return "kagi"

    @property
    def display_name(self) -> str:
        return "Kagi"

    def is_available(self) -> bool:
        """Return True when ``KAGI_API_KEY`` is set to a non-empty value."""
        return bool(os.getenv("KAGI_API_KEY", "").strip())

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return True

    def supports_crawl(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Execute a Kagi search."""
        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return {"success": False, "error": "Interrupted"}

            logger.info("Kagi search: '%s' (limit=%d)", query, limit)
            raw = _kagi_request(
                "search",
                {
                    "query": query,
                    "limit": min(limit, 100),
                },
            )
            return _normalize_kagi_search_results(raw)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kagi search error: %s", exc)
            return {"success": False, "error": f"Kagi search failed: {exc}"}

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        """Extract content from one or more URLs via Kagi."""
        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return [
                    {"url": u, "error": "Interrupted", "title": ""} for u in urls
                ]

            logger.info("Kagi extract: %d URL(s)", len(urls))
            pages = [{"url": u} for u in urls]
            raw = _kagi_request(
                "extract",
                {
                    "pages": pages,
                    "format": "json",
                },
            )
            return _normalize_kagi_extract(raw)
        except ValueError as exc:
            return [{"url": u, "title": "", "content": "", "error": str(exc)} for u in urls]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kagi extract error: %s", exc)
            return [
                {"url": u, "title": "", "content": "", "error": f"Kagi extract failed: {exc}"}
                for u in urls
            ]

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Kagi",
            "badge": "paid",
            "tag": "Premium search and content extraction.",
            "env_vars": [
                {
                    "key": "KAGI_API_KEY",
                    "prompt": "Kagi API key",
                    "url": "https://kagi.com/api/keys",
                },
            ],
        }
