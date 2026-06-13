from __future__ import annotations

import streamlit as st

from frontend import api
from frontend.labels import model_label
from frontend.state import apply_session


def render(pages: dict) -> None:
    with st.sidebar:
        st.markdown("## Valor-Auto")

        if st.button("＋  New chat", type="primary", use_container_width=True):
            apply_session(api.new_session())
            st.rerun()

        models = st.session_state.models
        current = st.session_state.rater_model
        idx = models.index(current) if current in models else 0
        choice = st.selectbox("Model", models, index=idx, format_func=model_label)
        if choice != current:
            api.patch_config(choice)
            st.session_state.rater_model = choice

        st.divider()
        st.caption("Recent")
        with st.container(height=320, border=False):
            _session_list()

        with st.container(key="sidebar_nav"):
            st.divider()
            for page in pages.values():
                st.page_link(page)


def _session_list() -> None:
    active = st.session_state.thread_id
    sessions = api.get_sessions()
    if not sessions:
        st.caption("No chats yet")
        return
    for s in sessions:
        if st.button(
            s["title"],
            key=f"sess::{s['thread_id']}",
            use_container_width=True,
            type="primary" if s["thread_id"] == active else "secondary",
        ):
            apply_session(api.get_session(s["thread_id"]))
            st.rerun()
