# valor-auto-agent

A used-car shopping agent for the Portuguese market. It scrapes **OLX** and **Standvirtual**,
rates every listing from 0–10 with the LLM of your choice, and gives you a persistent library to
review, annotate, and decide on the cars worth chasing.

---

## Features

- **Natural-language search** — type *"find me a bmw 320d under 10k"* and the agent extracts the
  filters and hands you a **pre-filled form to confirm**, rather than a blank one.
- **Long-term memory** — remembers your usual brand/budget and pre-fills the gaps a query leaves out.
- **Two-source crawl** — OLX and Standvirtual in parallel, behind their Cloudflare front.
- **LLM rating** — each batch is scored 0–10 using the batch itself as market context.
- **Pick your model** — rate with Claude (Opus / Sonnet / Haiku) or Gemini (2.5 / 3.x).
- **Saved searches + alerts** — watch a search; a scheduler re-runs it and alerts only on listings
  that appear after you started watching.
- **Compare + dedupe** — the same car cross-posted to both sites is grouped ("also on …"); select
  results to compare them side by side.
- **Persistent evaluations** — every rated car is saved; browse, filter, shortlist, and add notes.
- **Clean architecture** — a FastAPI backend over the domain core, a Next.js UI that only speaks HTTP.

## How it works

1. You describe what you want in the chat (e.g. *"find me a bmw 320d under 10k"*).
2. The agent extracts filters from the message, fills gaps from memory, and shows a **pre-filled
   form** to confirm or adjust.
3. On submit, both sites are scraped concurrently and the listings are persisted.
4. The rater scores the batch and the top picks come back with rationale, source links, and any
   cross-source duplicates flagged.
5. Every car lands in **Evaluations**, where your status and notes persist across sessions.

## Architecture

Three tiers with a real HTTP boundary — the UI never touches the database or the graph directly.

```
browser
  │
  ▼  http
Next.js (frontend-web/)  ──fetch──▶  FastAPI (backend/)
                                       │
                               valor_auto_agent (domain)
                                 graph · db · rater · crawler · scheduler
```

- **`valor_auto_agent/`** — the domain core and the only published Python package: LangGraph
  orchestration, the crawler, the rater sub-agent, memory, dedupe, and SQLite persistence.
- **`backend/`** — a FastAPI service; the only tier that talks to the graph and the database. Hosts
  the saved-search scheduler in its lifespan.
- **`frontend-web/`** — a Next.js (App Router) SPA that is a pure HTTP client of the backend.

## Stack

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- [LangGraph](https://langchain-ai.github.io/langgraph/) — orchestration, with `interrupt()` to
  confirm filters mid-flow and a SQLite checkpointer for conversation memory
- [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) — a stealth-patched Playwright
  fork, since both targets sit behind Cloudflare
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) — the backend
- [Next.js](https://nextjs.org/) 16 + React 19 + Tailwind v4 — the frontend (dark developer-console
  theme modelled on Google's `adk-web`)
- SQLAlchemy 2.0 + SQLite — persistence, plus a Markdown snapshot per scrape under `data/snapshots/`
- Anthropic + Google GenAI SDKs — the rater backends (Claude uses prompt caching)

## Quickstart

```bash
uv sync                          # python backend + domain deps
uv run patchright install chromium
make web-install                 # next.js frontend deps (npm)
cp .env.example .env             # then add your API key(s)
```

Requires Python 3.12, [uv](https://docs.astral.sh/uv/), and Node.js 20+.

## Configuration

Settings load from `.env`. Provider keys are read directly; everything else is `VALOR_`-prefixed.

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required for Claude rating and the chat/classifier nodes |
| `GEMINI_API_KEY` | — | Required to rate with Gemini models |
| `VALOR_RATER_MODEL` | `gemini-2.5-flash` | Default rater model (also selectable in the UI) |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | Backend URL the frontend calls (baked at build) |
| `VALOR_DB_URL` | `sqlite:///data/valor.db` | Listings, ratings, and evaluations store |
| `VALOR_CHECKPOINT_DB` | `data/checkpoints.db` | LangGraph conversation checkpoints |
| `VALOR_HEADLESS` | `true` | Run the browser headless |
| `VALOR_MAX_PAGES` | `3` | Result pages to crawl per source |

> You only need a key for the provider you actually rate with. With just a Gemini key, search and
> rating still work; only the free-form chat assistant needs an Anthropic key.

## Running

The fastest path is `make`, which starts the backend and frontend together (Ctrl-C stops both):

```bash
make web-install  # once, to install frontend deps
make run          # backend (:8000) + next.js dev server (:3000)
make run-docker   # build the image and run both in one container
```

Then open the frontend at <http://localhost:3000>.

Prefer to run them by hand? They are two processes — in separate terminals:

```bash
# backend (keep to a single worker — one shared graph + SQLite checkpoint connection)
uv run uvicorn backend.main:app --app-dir src

# frontend
cd frontend-web && npm run dev
```

### Docker

The image bundles the patched Chromium needed for scraping, a uv-managed Python backend, and the
Next.js frontend built into a standalone Node server:

```bash
make run-docker
# or by hand:
docker build -t valor-auto-agent .
docker run --rm -it --env-file .env -p 8000:8000 -p 3000:3000 valor-auto-agent
```

The frontend is served on `:3000` inside the container.

## Using the app

- **Chat** — describe the car; confirm the pre-filled filter form; get the top picks with rationale,
  source links, and "also on …" badges for cross-posted listings. Tick results to compare them.
- **Saved & alerts** — save a search with a re-run cadence; the scheduler watches it and lists new
  matches (the first run sets a baseline so you aren't flooded with existing listings).
- **Evaluations** — your full rated-car library. Filter by text, score, or status; edit `status`
  and `notes` inline and they persist.
- **Sidebar** — pick the rater model, start a fresh chat, and jump between recent sessions.

## Development

```bash
make test                # uv run pytest
make lint                # ruff + next lint
uv run ruff format .     # format
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
