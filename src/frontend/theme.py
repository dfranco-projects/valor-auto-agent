from __future__ import annotations

import streamlit as st

# streamlit only pushes its toml theme at connection time, so a live light/dark
# toggle has to be done with css; this restyles the main surfaces for dark mode
_DARK_CSS = """
<style>
  .stApp {
    background-color: #0e1117 !important;
    color: #e8eaed !important;
  }
  [data-testid="stHeader"] { background: transparent !important; }
  [data-testid="stSidebar"],
  [data-testid="stSidebarContent"] {
    background-color: #191c24 !important;
  }
  .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp span,
  .stApp label, .stApp li, .stApp small {
    color: #e8eaed !important;
  }
  [data-baseweb="input"],
  [data-baseweb="textarea"],
  [data-baseweb="select"] > div,
  [data-testid="stChatInput"] textarea {
    background-color: #0e1117 !important;
    color: #e8eaed !important;
  }
  [data-testid="stChatInput"],
  [data-testid="stChatMessage"] {
    background-color: #191c24 !important;
  }
  .stButton button {
    background-color: #262a35 !important;
    color: #e8eaed !important;
    border-color: #3a3f4b !important;
  }
  .stButton button[kind="primary"] {
    background-color: #2563eb !important;
    color: #ffffff !important;
  }
  [data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #2a2f3a !important;
  }
</style>
"""


def apply(theme: str | None) -> None:
    if theme == "dark":
        st.markdown(_DARK_CSS, unsafe_allow_html=True)
