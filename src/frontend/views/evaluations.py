from __future__ import annotations

import pandas as pd
import streamlit as st

from frontend import api

STATUS_OPTIONS = ["", "shortlist", "maybe", "rejected"]
DISPLAY_COLS = [
    "status",
    "notes",
    "brand",
    "model",
    "title",
    "year",
    "km",
    "price_eur",
    "fuel",
    "transmission",
    "location",
    "score",
    "rated_by",
    "source",
    "url",
]


def render() -> None:
    st.title("valor · evaluations")
    st.caption("every car you've rated — set a status and notes; decisions persist")

    rows = _query()
    if not rows:
        st.info("no evaluations yet — run a search first")
        return

    df = pd.DataFrame(rows)
    df["status"] = df["status"].fillna("")
    df["notes"] = df["notes"].fillna("")
    df = df[[c for c in DISPLAY_COLS if c in df.columns]]

    st.data_editor(
        df,
        key="eval_editor",
        use_container_width=True,
        hide_index=True,
        disabled=[c for c in df.columns if c not in ("status", "notes")],
        column_config={
            "status": st.column_config.SelectboxColumn(
                "status", options=STATUS_OPTIONS, width="small"
            ),
            "notes": st.column_config.TextColumn("notes", width="medium"),
            "price_eur": st.column_config.NumberColumn("price €"),
            "score": st.column_config.NumberColumn("score", format="%.1f"),
            "rated_by": st.column_config.TextColumn("rated by"),
            "url": st.column_config.LinkColumn("link", display_text="open"),
        },
    )
    _persist_edits(rows)


def _query() -> list[dict]:
    with st.expander("filters", expanded=False):
        c1, c2, c3 = st.columns(3)
        search = c1.text_input("search title / brand / location", "")
        sources = c2.multiselect("source", ["olx", "standvirtual"])
        min_score = c3.slider("min score", 0.0, 10.0, 0.0, 0.5)
        statuses = st.multiselect("status", ["shortlist", "maybe", "rejected", "unset"])
    return api.get_evaluations(
        search=search or None,
        sources=sources or None,
        min_score=min_score or None,
        statuses=statuses or None,
    )


def _persist_edits(rows: list[dict]) -> None:
    delta = st.session_state.get("eval_editor", {}).get("edited_rows", {})
    for idx, changes in delta.items():
        row = rows[int(idx)]
        status = (changes.get("status", row.get("status")) or "").strip() or None
        notes = changes.get("notes", row.get("notes")) or ""
        api.patch_decision(row["source"], row["external_id"], status, notes)
