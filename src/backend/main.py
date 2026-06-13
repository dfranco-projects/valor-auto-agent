from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.deps import get_graph
from backend.routers import config, evaluations, search, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_graph()  # compile the graph up front so the first request isn't slow
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
