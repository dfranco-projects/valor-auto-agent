from __future__ import annotations

from functools import lru_cache

from valor_auto_agent.config import Settings, load
from valor_auto_agent.graph.builder import build


@lru_cache
def get_graph():
    # one compiled graph per process; its sqlite checkpoint conn is check_same_thread=False
    return build()


def get_settings() -> Settings:
    return load()
