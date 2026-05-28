# valor-auto-agent

portuguese used-car agent that scrapes **olx.pt** and **standvirtual.com**, persists listings to sqlite + markdown snapshots, then rates the batch 0-10 with a claude sub-agent and surfaces the top 10.

## stack

- python 3.12 + uv
- langgraph orchestration with `interrupt()` for collecting user filters mid-flow
- patchright (stealth-patched playwright fork) for the crawler — both targets sit behind cloudflare
- sqlalchemy 2.0 + sqlite for persistence, markdown snapshot per scrape under `data/snapshots/`
- streamlit frontend
- anthropic sdk + prompt caching for the rater sub-agent

## flow

1. user asks for cars in the streamlit chat
2. agent confirms "run crawler?"; on yes the graph hits an `interrupt()`
3. ui renders a filter form (brand, model, year, price, km, fuel, transmission, location)
4. on submit, crawler scrapes olx + standvirtual concurrently
5. listings persisted to sqlite + a markdown snapshot is written
6. rater sub-agent scores every listing 0-10 using the batch itself as market context
7. top 10 returned with rationale and source links

## setup

```bash
uv sync
uv run patchright install chromium
cp .env.example .env  # then set ANTHROPIC_API_KEY
```

## run

```bash
uv run streamlit run src/valor_auto_agent/app.py
```

## tests

```bash
uv run pytest
```

## code style

- ruff (line length 100, py312 target) — `uv run ruff check . && uv run ruff format .`
- comments lowercase, no trailing period
- no comments explaining *what* the code does — only *why* when non-obvious

## layout

```
src/valor_auto_agent/
  app.py                # streamlit entrypoint
  config.py             # pydantic-settings env loader
  cli.py                # uv script entrypoint
  graph/                # langgraph wiring + nodes + state
  subagents/rater.py    # claude rater sub-agent
  tools/crawler/        # patchright + per-site builders/parsers
  db/                   # sqlalchemy models, session, md export
  prompts/rater.md      # cached rater system prompt
```

## scope notes

- single local user, no auth, no multi-tenant
- sqlite only (no postgres)
- no external valuation api (rater works off the scraped batch as market context)
- cloudflare may rate-limit aggressive runs; proxy support is a follow-up, not in the initial commit
