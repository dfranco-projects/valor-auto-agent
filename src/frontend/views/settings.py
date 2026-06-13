from __future__ import annotations

import streamlit as st

THEMES = {"Light": "light", "Dark": "dark"}


def render() -> None:
    st.title("Settings")

    st.subheader("Theme")
    current = st.session_state.get("theme", "light")
    default = next((k for k, v in THEMES.items() if v == current), "Light")
    choice = st.segmented_control(
        "Appearance", list(THEMES), default=default, label_visibility="collapsed"
    )
    if choice and THEMES[choice] != current:
        st.session_state.theme = THEMES[choice]
        st.rerun()
