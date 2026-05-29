from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from valor_auto_agent.config import load
from valor_auto_agent.graph.nodes import (
    chat,
    collect_filters,
    decide,
    present,
    rate,
    route_decide,
    scrape,
)
from valor_auto_agent.graph.state import AgentState


def build(checkpoint_db: str | None = None):
    settings = load()
    path = checkpoint_db or settings.checkpoint_db
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    saver = SqliteSaver(conn)

    g = StateGraph(AgentState)
    g.add_node("decide", decide)
    g.add_node("collect_filters", collect_filters)
    g.add_node("scrape", scrape)
    g.add_node("rate", rate)
    g.add_node("present", present)
    g.add_node("chat", chat)

    g.add_edge(START, "decide")
    g.add_conditional_edges(
        "decide", route_decide, {"collect_filters": "collect_filters", "chat": "chat"}
    )
    g.add_edge("collect_filters", "scrape")
    g.add_edge("scrape", "rate")
    g.add_edge("rate", "present")
    g.add_edge("present", END)
    g.add_edge("chat", END)

    return g.compile(checkpointer=saver)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    graph = build()
    if args.dry_run:
        print("nodes:", list(graph.get_graph().nodes))
        return


if __name__ == "__main__":
    main()
