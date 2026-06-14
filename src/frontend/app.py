from __future__ import annotations

import sys
from pathlib import Path

# put src/ on the path so `frontend.*` resolves when streamlit runs this file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from frontend import sidebar  # noqa: E402
from frontend.state import init_session_state  # noqa: E402
from frontend.views import chat, evaluations  # noqa: E402

st.set_page_config(page_title="Valor-Auto", layout="wide")

st.markdown(
    """
    <style>
      footer {visibility: hidden;}
      section[data-testid="stSidebar"] {width: 300px !important;}
      /* make the sidebar a full-height flex column so the nav can pin to the bottom */
      [data-testid="stSidebarContent"] {
        display: flex;
        flex-direction: column;
        min-height: calc(100vh - 2rem);
      }
      [data-testid="stSidebarContent"] [data-testid="stVerticalBlock"]:first-of-type {
        flex: 1 1 auto;
      }
      .st-key-sidebar_nav {margin-top: auto;}
      .block-container {padding-top: 2.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

init_session_state()

pages = {
    # the default page is always served at "/", so it must NOT set url_path
    # (otherwise its page_link points at /chat and 404s)
    "chat": st.Page(chat.render, title="Chat", icon=":material/chat:", default=True),
    "evaluations": st.Page(
        evaluations.render,
        title="Evaluations",
        icon=":material/directions_car:",
        url_path="evaluations",
    ),
}

nav = st.navigation(list(pages.values()), position="hidden")
sidebar.render(pages)
nav.run()
