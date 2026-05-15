# hermes-kagi-plugin

Kagi web search and content extraction for [Hermes Agent](https://hermes-agent.nousresearch.com/).

## What it does

Replaces the default `web_search` and `web_extract` backends with [Kagi](https://kagi.com) — the search engine that actually respects its users.

- **Search**: `web_search` routes through Kagi's v1 search API
- **Extract**: URL content extraction via Kagi's v1 extract API (reads full page content as markdown)
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
├── __init__.py      # registers the provider
└── provider.py      # Kagi v1 API implementation
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

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `KAGI_API_KEY` | Yes | Your Kagi v1 API key |

## Files

| File | Purpose |
|------|---------|
| [`provider.py`](provider.py) | `KagiWebSearchProvider` — search + extract implementation |
| [`__init__.py`](__init__.py) | Plugin entry point, registers with `ctx.register_web_search_provider()` |
| [`plugin.yaml`](plugin.yaml) | Hermes plugin manifest (`kind: backend`) |

## API coverage

| Endpoint | Hermes mapping | Status |
|----------|---------------|--------|
| `POST /api/v1/search` | `web_search` | ✅ Working |
| `POST /api/v1/extract` | `web_extract` | ✅ Working |
| `POST /api/v1/summarize` | — | ❌ Not implemented |

## Known issues

- Kagi's v1 search occasionally returns no results for broad queries; the plugin falls back through news → video → podcast → interesting finds → code categories when that happens.
- No support for Kagi's "enrichment" features (summarization, discussion, etc.) — these could be added later if there's interest.

## Credits

Written by [Samuel Proulx](https://github.com/fastfinge), with help from [Nous](https://nousresearch.com/) — both of us wanted Kagi search that actually worked.

## License

MIT — do whatever you want, just don't blame us if your API bill explodes.
