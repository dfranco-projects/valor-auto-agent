from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.routers import config, evaluations, search, sessions
from valor_auto_agent.config import load


def _setup_logging() -> None:
    # surface the crawler/graph logs in the uvicorn console (own handler so uvicorn
    # config doesn't swallow them)
    logger = logging.getLogger("valor_auto_agent")
    if not logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
        logger.propagate = False


_setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # nodes are async; hold an async sqlite checkpointer open for the app's lifetime
    path = load().checkpoint_db
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        from valor_auto_agent.graph.builder import build_graph

        app.state.graph = build_graph(saver)
        yield


def create_app() -> FastAPI:
    app = FastAPI(title="valor-auto-agent", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for r in (search.router, evaluations.router, sessions.router, config.router):
        app.include_router(r)
    return app


app = create_app()
