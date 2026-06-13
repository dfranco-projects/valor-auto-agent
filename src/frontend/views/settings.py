from __future__ import annotations

import streamlit as st

from frontend import api
from frontend.components import key_badges


def render() -> None:
    st.title("valor · settings")

    st.subheader("rater model")
    models = st.session_state.models
    current = st.session_state.rater_model
    idx = models.index(current) if current in models else 0
    choice = st.selectbox("model used to rate listings", models, index=idx)
    if choice != current:
        api.patch_config(choice)
        st.session_state.rater_model = choice
        st.success(f"rater model set to {choice}")

    st.subheader("api keys")
    key_badges(st.session_state.key_status)
    st.caption("set ANTHROPIC_API_KEY / GEMINI_API_KEY in .env, then restart the backend")

    st.subheader("session")
    st.write(f"active thread: `{st.session_state.thread_id}`")
    if st.button("new session", type="primary"):
        sess = api.new_session()
        st.session_state.thread_id = sess["thread_id"]
        st.session_state.history = []
        st.session_state.top = []
        st.session_state.pending_filters = False
        st.rerun()

    with st.expander("check session state"):
        st.json({k: v for k, v in st.session_state.items() if not k.startswith("_")})
