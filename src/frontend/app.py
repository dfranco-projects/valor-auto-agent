from __future__ import annotations

import sys
from pathlib import Path

# put src/ on the path so `frontend.*` resolves when streamlit runs this file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from frontend.state import init_session_state  # noqa: E402
from frontend.views import chat, evaluations, settings  # noqa: E402

st.set_page_config(page_title="valor", page_icon="🚗", layout="wide")
init_session_state()

nav = st.navigation(
    {
        "Search": [
            st.Page(
                chat.render, title="Chat", icon=":material/chat:", url_path="chat", default=True
            )
        ],
        "Library": [
            st.Page(
                evaluations.render,
                title="Evaluations",
                icon=":material/directions_car:",
                url_path="evaluations",
            ),
            st.Page(
                settings.render, title="Settings", icon=":material/settings:", url_path="settings"
            ),
        ],
    }
)
nav.run()
