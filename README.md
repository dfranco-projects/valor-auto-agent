# valor-auto-agent

Your personal used-car scout for the Portuguese market. Tell it what you're looking for in plain
language — it searches **OLX** and **Standvirtual** for you, scores every listing 0–10 with an LLM,
and keeps a persistent library of every car it has rated so you can shortlist, annotate, and decide
without juggling browser tabs.

---

## What it does

- **You talk, it searches.** Type *"find me a bmw 320d under 10k"* — it figures out the filters and
  shows you a pre-filled form to confirm, not a blank one to fill in.
- **It learns your taste.** Your usual brand and budget are remembered and used to fill in whatever
  a query leaves out.
- **It searches both major sites at once** and shows live progress while it scrapes, rates, and
  inspects.
- **Every car gets a score and a reason.** Listings are rated 0–10 against the rest of the batch,
  so "good deal" means good *relative to what's on the market right now*.
- **Top picks can get a second look.** The best candidates are inspected in depth — photos and the
  full description — to refine their score.
- **Spot the duplicates.** The same car posted on both sites is grouped, with an "also on …" badge.
- **Compare side by side.** Tick two or more results to see them in one table.
- **Watch a search.** Save it with a re-run cadence and get alerted only about listings that appear
  *after* you started watching — no flood of what's already there.
- **Nothing gets lost.** Every rated car lands in your Evaluations library, where your status and
  notes persist across sessions.
- **Pick your judge.** Rate with Claude (Opus / Sonnet / Haiku) or Gemini (2.5 / 3.x), switchable
  from the sidebar.

## Getting started

You need Python 3.12, [uv](https://docs.astral.sh/uv/), and Node.js 20+.

```bash
uv sync                             # install backend dependencies
uv run patchright install chromium  # the browser used for scraping
make web-install                    # install frontend dependencies
cp .env.example .env                # then add your API key(s)
```

You only need a key for the provider you rate with. With just a `GEMINI_API_KEY`, search and rating
work fully; an `ANTHROPIC_API_KEY` additionally enables the free-form chat assistant.

Then start everything (Ctrl-C stops both):

```bash
make run
```

and open <http://localhost:3000>.

Prefer Docker? `make run-docker` builds and runs backend + frontend in one container, frontend on
`:3000`.

## Using the app

- **Chat** — describe the car you want; confirm the pre-filled filter form; watch the progress as
  it scrapes and rates; get top picks with a score, a rationale, source links, and duplicate
  badges. Tick results to compare them.
- **Saved & alerts** — save a search to watch it; the scheduler re-runs it and lists only new
  matches since you started watching.
- **Evaluations** — your full rated-car library. Filter by text, score, or status; edit status and
  notes inline and they stick.
- **Sidebar** — switch the rater model, start a fresh chat, jump between recent sessions.

## Configuration

Settings load from `.env`. The ones you're most likely to touch:

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Rate with Claude models + the chat assistant |
| `GEMINI_API_KEY` | — | Rate with Gemini models |
| `VALOR_RATER_MODEL` | `gemini-2.5-flash` | Default rater (also switchable in the UI) |
| `VALOR_MAX_PAGES` | `3` | Result pages to crawl per site — more pages, longer searches |
| `VALOR_HEADLESS` | `true` | Set `false` to watch the scraping browser work |
| `VALOR_DB_URL` | `sqlite:///data/valor.db` | Where listings, ratings, and evaluations live |
| `VALOR_CHECKPOINT_DB` | `data/checkpoints.db` | Conversation memory |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | Backend URL the frontend calls (baked at build) |

## Good to know

- Built for a single local user — no accounts, no auth.
- The sites sit behind Cloudflare; very aggressive settings may get throttled.
- Scores come from comparing the batch against itself — there's no external valuation service.
- Each search also writes a Markdown snapshot under `data/snapshots/` you can read or diff later.
- The intent classifier and chat assistant currently run on Claude Haiku regardless of the selected
  rater model.

## Under the hood

Three tiers with a real HTTP boundary — the UI never touches the database or the agent directly:

```
browser ──▶ Next.js (frontend-web/) ──fetch──▶ FastAPI (src/backend/)
                                                  │
                                        valor_auto_agent (domain core)
                                     graph · crawler · rater · db · scheduler
```

- **`src/valor_auto_agent/`** — the domain core: LangGraph orchestration (with `interrupt()` for
  the filter-confirm step and SQLite checkpoints for conversation memory), the Patchright-driven
  crawler (a stealth Playwright fork, for the Cloudflare front), the rater and inspector
  sub-agents, memory, dedupe, and SQLAlchemy/SQLite persistence.
- **`src/backend/`** — FastAPI + Uvicorn; the only tier that talks to the graph and database.
  Streams search progress over SSE and hosts the saved-search scheduler. Keep it to a single
  worker — one shared graph and checkpoint connection.
- **`frontend-web/`** — Next.js 16 + React 19 + Tailwind v4; a pure HTTP client of the backend.

### Development

```bash
make test                # backend test suite (offline)
uv run pytest -m live    # opt-in tests against the real sites
make lint                # ruff + next lint
uv run ruff format .     # format
```

CI runs ruff (check + format), mypy, the offline tests, and the frontend lint + build on every PR.
Conventions: 100-char lines, Python 3.12 target, lowercase comments, and no comments that merely
restate the code.
