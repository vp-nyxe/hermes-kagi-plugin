# hermes-kagi-plugin

Kagi web search, content extraction, and enriched search for [Hermes Agent](https://hermes-agent.nousresearch.com/).

## What it does

Replaces the default `web_search` and `web_extract` backends with [Kagi](https://kagi.com) — the search engine that actually respects its users. Plus a bonus `kagi_enriched_search` tool that exposes Kagi's full enrichment data (infoboxes, adjacent questions, interesting finds, related searches, etc.).

- **Search**: `web_search` routes through Kagi's v1 search API
- **Extract**: URL content extraction via Kagi's v1 extract API (reads full page content as markdown)
- **Enriched Search**: `kagi_enriched_search` returns the full Kagi response with all special categories
- **No crawl support** — Kagi doesn't expose a crawl endpoint

## Why not the official Kagi MCP server?

The [kagimcp](https://github.com/kagisearch/kagimcp) server targets Kagi's **v0** API, which requires a separate API key scope. This plugin targets the **v1** API — the same key you already use for `/api/v1/extract`.

## Prerequisites

- Hermes Agent (tested on 2025.x, should work on newer)
- A [Kagi API key](https://kagi.com/api/keys) with v1 access
- `httpx` (already pulled in by Hermes)

## Installation

### Option 1: Drop-in (quickest)

```bash
cd ~/.hermes/plugins
git clone https://github.com/fastfinge/hermes-kagi-plugin.git web-kagi
```

Then enable it:

```yaml
# ~/.hermes/config.yaml
plugins:
  enabled:
    - web-kagi

web:
  backend: "kagi"
```

### Option 2: As a Hermes plugin directory

Copy the files to `~/.hermes/plugins/web-kagi/`:

```
web-kagi/
├── plugin.yaml      # manifest
├── __init__.py      # registers the provider + enriched search tool
├── provider.py      # Kagi v1 API implementation (search + extract)
└── tools.py         # kagi_enriched_search tool
```

Set your API key:

```bash
# ~/.hermes/.env
KAGI_API_KEY=your-key-here
```

Reload Hermes.

## Configuration

```yaml
web:
  # Use Kagi for both search and extract
  backend: "kagi"

  # Or split them:
  search_backend: "kagi"
  extract_backend: "kagi"
```

## Tools

### `kagi_enriched_search`

A dedicated tool that surfaces all the enrichment data Kagi returns — stuff the standard Hermes `web_search` contract strips out.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | (required) | Search query |
| `workflow` | string | `"search"` | Type of results: `search`, `images`, `videos`, `news`, `podcasts` |
| `limit` | integer | `10` | Max results (1–100) |
| `include_enrichment` | boolean | `true` | Include infoboxes, adjacent questions, interesting finds, related searches, direct answers |

**Response structure:**

```json
{
  "success": true,
  "query": "best programming language 2025",
  "workflow": "search",
  "web_results": [...],
  "images": [...],
  "videos": [...],
  "news": [...],
  "infobox": [...],
  "adjacent_questions": [...],
  "direct_answers": [...],
  "related_searches": [...],
  "interesting_finds": [...],
  "interesting_news": [...],
  "listicles": [...],
  "code_results": [...],
  "package_tracking": [...],
  "weather": [...],
  "web_archive": [...]
}
```

Only categories that actually have results are included. Empty categories are omitted.

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `KAGI_API_KEY` | Yes | Your Kagi v1 API key |

## Files

| File | Purpose |
|------|---------|
| [`provider.py`](provider.py) | `KagiWebSearchProvider` — search + extract implementation |
| [`tools.py`](tools.py) | `kagi_enriched_search` tool with full enrichment data |
| [`__init__.py`](__init__.py) | Plugin entry point — registers provider + tool |
| [`plugin.yaml`](plugin.yaml) | Hermes plugin manifest (`kind: backend`) |

## API coverage

| Endpoint | Hermes mapping | Status |
|----------|---------------|--------|
| `POST /api/v1/search` | `web_search` | ✅ Working |
| `POST /api/v1/search` | `kagi_enriched_search` | ✅ Working |
| `POST /api/v1/extract` | `web_extract` | ✅ Working |
| `POST /api/v0/summarize` | — | ❌ Not implemented (requires separate v0 key) |

## Known issues

- Kagi's v1 search occasionally returns no results for broad queries; the plugin falls back through news → video → podcast → interesting finds → code categories when that happens.
- Summarization is not supported because Kagi's Summarizer API is v0-only and requires a separate API key scope.

## Credits

Written by [Samuel Proulx](https://github.com/fastfinge), with help from [Nous](https://nousresearch.com/).

## License

MIT — do whatever you want, just don't blame us if your API bill explodes.
