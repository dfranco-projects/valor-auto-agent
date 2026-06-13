# valor-auto-agent

A used-car shopping agent for the Portuguese market. It scrapes **OLX** and **Standvirtual**,
rates every listing from 0–10 with the LLM of your choice, and gives you a persistent library to
review, annotate, and decide on the cars worth chasing.

---

## Features

- **Two-source crawl** — OLX and Standvirtual in parallel, behind their Cloudflare front.
- **LLM rating** — each batch is scored 0–10 using the batch itself as market context.
- **Pick your model** — rate with Claude (Opus / Sonnet / Haiku) or Gemini (2.5 Pro / Flash).
- **Persistent evaluations** — every rated car is saved; browse, filter, shortlist, and add notes.
- **Decision tracking** — mark each car `shortlist` / `maybe` / `rejected` with free-text notes.
- **Clean architecture** — a FastAPI backend over the domain core, a Streamlit UI that only speaks HTTP.

## How it works

1. You describe what you want in the chat (e.g. *"find me a bmw 320d under 15k"*).
2. The agent confirms intent and asks for structured filters (brand, year, price, km, fuel, …).
3. On submit, both sites are scraped concurrently and the listings are persisted.
4. The rater scores the batch and the top picks come back with rationale and source links.
5. Every car lands in **Evaluations**, where your status and notes persist across sessions.

## Architecture

Three tiers with a real HTTP boundary — the UI never touches the database or the graph directly.

```
browser
  │
  ▼  http
Streamlit (frontend/)  ──httpx──▶  FastAPI (backend/)
                                      │
                              valor_auto_agent (domain)
                                graph · db · rater · crawler
```

- **`valor_auto_agent/`** — the domain core and the only published package: LangGraph
  orchestration, the crawler, the rater sub-agent, and SQLite persistence.
- **`backend/`** — a FastAPI service; the only tier that talks to the graph and the database.
- **`frontend/`** — a Streamlit app that is a pure HTTP client of the backend.

## Stack

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- [LangGraph](https://langchain-ai.github.io/langgraph/) — orchestration, with `interrupt()` to
  collect filters mid-flow and a SQLite checkpointer for conversation memory
- [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) — a stealth-patched Playwright
  fork, since both targets sit behind Cloudflare
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) — the backend
- [Streamlit](https://streamlit.io/) — the frontend
- SQLAlchemy 2.0 + SQLite — persistence, plus a Markdown snapshot per scrape under `data/snapshots/`
- Anthropic + Google GenAI SDKs — the rater backends (Claude uses prompt caching)

## Quickstart

```bash
uv sync
uv run patchright install chromium
cp .env.example .env   # then add your API key(s)
```

## Configuration

Settings load from `.env`. Provider keys are read directly; everything else is `VALOR_`-prefixed.

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required for Claude rating and the chat/classifier nodes |
| `GEMINI_API_KEY` | — | Required to rate with Gemini models |
| `VALOR_RATER_MODEL` | `claude-sonnet-4-6` | Default rater model (also selectable in the UI) |
| `VALOR_API_BASE` | `http://localhost:8000` | Backend URL the frontend calls |
| `VALOR_DB_URL` | `sqlite:///data/valor.db` | Listings, ratings, and evaluations store |
| `VALOR_CHECKPOINT_DB` | `data/checkpoints.db` | LangGraph conversation checkpoints |
| `VALOR_HEADLESS` | `true` | Run the browser headless |
| `VALOR_MAX_PAGES` | `3` | Result pages to crawl per source |

> You only need a key for the provider you actually rate with. With just a Gemini key, search and
> rating still work; only the free-form chat assistant needs an Anthropic key.

## Running

The fastest path is `make`, which starts the backend and frontend together (Ctrl-C stops both):

```bash
make run          # both processes locally
make run-docker   # build the image and run both in one container
```

Then open the Streamlit URL (default <http://localhost:8501>).

Prefer to run them by hand? They are two processes — in separate terminals:

```bash
# backend (keep to a single worker — one shared graph + SQLite checkpoint connection)
uv run uvicorn backend.main:app --app-dir src

# frontend
uv run streamlit run src/frontend/app.py
```

### Docker

The image runs both processes and bundles the patched Chromium needed for scraping:

```bash
make run-docker
# or by hand:
docker build -t valor-auto-agent .
docker run --rm -it --env-file .env -p 8000:8000 -p 8501:8501 valor-auto-agent
```

## Using the app

- **Chat** — describe the car, fill the filter form, and get the top picks with rationale and links.
- **Evaluations** — your full rated-car library. Filter by text, source, score, or status; edit
  `status` and `notes` inline and they persist. Brand and model are taken from the search's filters
  (the parsers don't split them out of the listing title).
- **Settings** — choose the rater model, see which API keys are configured, inspect the current
  session state, and start a fresh session.

## Development

```bash
uv run pytest                                  # tests
uv run ruff check . && uv run ruff format .    # lint + format
```

Conventions: 100-char lines, Python 3.12 target, lowercase comments, and no comments that merely
restate the code.

## Scope & roadmap

- Single local user — no auth, no multi-tenancy.
- SQLite only; the SQLAlchemy URL can be pointed at Postgres later if it ever goes multi-user.
- No external valuation API — the rater works off the scraped batch as its own market context.
- Cloudflare may throttle aggressive runs; proxy support is a possible follow-up.
- The intent classifier and chat assistant currently run on Claude Haiku regardless of the selected
  rater model — making them provider-agnostic is a future improvement.
```
