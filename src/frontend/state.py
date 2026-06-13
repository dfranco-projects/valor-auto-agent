from __future__ import annotations

import streamlit as st

from frontend import api


def apply_session(data: dict) -> None:
    st.session_state.thread_id = data["thread_id"]
    st.session_state.history = [tuple(h) for h in data.get("history", [])]
    st.session_state.top = data.get("top", [])
    st.session_state.pending_filters = False
    if data.get("rater_model"):
        st.session_state.rater_model = data["rater_model"]


def init_session_state() -> None:
    if st.session_state.get("_booted"):
        return
    cfg = api.get_config()
    st.session_state.models = cfg["models"]
    st.session_state.key_status = {"anthropic": cfg["anthropic_key"], "gemini": cfg["gemini_key"]}
    st.session_state.rater_model = cfg["default_model"]
    st.session_state.filter_schema = None
    apply_session(api.get_active_session())
    st.session_state._booted = True
