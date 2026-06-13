from __future__ import annotations

import streamlit as st


def result_card(i: int, t: dict) -> None:
    price = f"{t['price_eur']}€" if t.get("price_eur") else "n/a"
    with st.container(border=True):
        st.markdown(
            f"**{i}. [{t['score']:.1f}] {t['title']}** — {price} · "
            f"{t.get('year') or ''} · {t.get('km') or ''}km · {t['source']}"
        )
        if t.get("rationale"):
            st.caption(t["rationale"])
        st.link_button("open listing", t["url"])
