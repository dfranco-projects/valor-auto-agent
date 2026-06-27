from __future__ import annotations

from fastapi import Request

from valor_auto_agent.config import Settings, load


def get_graph(request: Request):
    # the compiled graph is created once in the app lifespan (with an async checkpointer)
    return request.app.state.graph


def get_settings() -> Settings:
    return load()
