from __future__ import annotations

import streamlit as st

from frontend import api


def init_session_state() -> None:
    if st.session_state.get("_booted"):
        return
    cfg = api.get_config()
    sess = api.get_active_session()
    st.session_state.models = cfg["models"]
    st.session_state.key_status = {"anthropic": cfg["anthropic_key"], "gemini": cfg["gemini_key"]}
    st.session_state.rater_model = sess.get("rater_model") or cfg["default_model"]
    st.session_state.thread_id = sess["thread_id"]
    st.session_state.history = [tuple(h) for h in sess.get("history", [])]
    st.session_state.top = sess.get("top", [])
    st.session_state.pending_filters = False
    st.session_state.filter_schema = None
    st.session_state._booted = True
