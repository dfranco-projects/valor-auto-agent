from __future__ import annotations

import asyncio
import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from valor_auto_agent.graph.builder import build

st.set_page_config(page_title="valor-auto-agent", page_icon=":car:")
st.title("valor-auto-agent")
st.caption("portuguese used-car agent — olx + standvirtual + claude rater")


@st.cache_resource
def get_graph():
    return build()


if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "history" not in st.session_state:
    st.session_state.history = []  # list[(role, content)]
if "pending_filters" not in st.session_state:
    st.session_state.pending_filters = False
if "top" not in st.session_state:
    st.session_state.top = []


graph = get_graph()
cfg = {"configurable": {"thread_id": st.session_state.thread_id}}


def _drain_messages(events):
    last_ai = None
    interrupted = False
    for ev in events:
        for _node, payload in ev.items() if isinstance(ev, dict) else []:
            if isinstance(payload, dict):
                for m in payload.get("messages", []) or []:
                    if isinstance(m, AIMessage):
                        last_ai = m.content
    state = graph.get_state(cfg)
    if state.next and "collect_filters" in state.next:
        interrupted = True
    return last_ai, interrupted


def _run_invoke(input_state):
    return asyncio.run(graph.ainvoke(input_state, cfg))


def _resume_with(values: dict):
    return asyncio.run(graph.ainvoke(Command(resume=values), cfg))


for role, content in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)

if st.session_state.pending_filters:
    st.info("filters needed — fill the form below to start the scrape")
    with st.form("filters"):
        c1, c2 = st.columns(2)
        with c1:
            brand = st.text_input("brand", "")
            model = st.text_input("model", "")
            year_min = st.number_input("year min", min_value=1980, max_value=2026, value=2015)
            year_max = st.number_input("year max", min_value=1980, max_value=2026, value=2024)
            km_max = st.number_input(
                "km max", min_value=0, max_value=500000, value=200000, step=5000
            )
        with c2:
            price_min = st.number_input(
                "price min €", min_value=0, max_value=200000, value=0, step=500
            )
            price_max = st.number_input(
                "price max €", min_value=0, max_value=200000, value=20000, step=500
            )
            fuel = st.selectbox("fuel", ["", "gasolina", "diesel", "hibrido", "eletrico", "gpl"])
            transmission = st.selectbox("transmission", ["", "manual", "automatica"])
            location = st.text_input("location", "")
        submitted = st.form_submit_button("scrape")
        if submitted:
            values = {
                "brand": brand or None,
                "model": model or None,
                "year_min": int(year_min) or None,
                "year_max": int(year_max) or None,
                "price_min": int(price_min) or None,
                "price_max": int(price_max) or None,
                "km_max": int(km_max) or None,
                "fuel": fuel or None,
                "transmission": transmission or None,
                "location": location or None,
            }
            values = {k: v for k, v in values.items() if v not in (None, "")}
            with st.spinner("scraping olx + standvirtual and rating..."):
                result = _resume_with(values)
            st.session_state.pending_filters = False
            top = result.get("top") or []
            st.session_state.top = top
            reply = result.get("reply") or "done"
            st.session_state.history.append(("assistant", reply))
            st.rerun()

if st.session_state.top:
    st.subheader("top 10")
    for i, t in enumerate(st.session_state.top, 1):
        price = f"{t['price_eur']}€" if t.get("price_eur") else "n/a"
        with st.container(border=True):
            st.markdown(
                f"**{i}. [{t['score']:.1f}] {t['title']}** — {price} · "
                f"{t.get('year') or ''} · {t.get('km') or ''}km · {t['source']}"
            )
            st.caption(t.get("rationale", ""))
            st.link_button("open listing", t["url"])

prompt = st.chat_input("ask the agent (e.g. find me a bmw 320d under 15k)")
if prompt:
    st.session_state.history.append(("user", prompt))
    with st.spinner("thinking..."):
        result = _run_invoke({"messages": [HumanMessage(content=prompt)]})
    state = graph.get_state(cfg)
    if state.next and "collect_filters" in state.next:
        st.session_state.pending_filters = True
        st.session_state.history.append(("assistant", "filters needed — open the form below"))
    else:
        reply = result.get("reply") or "(no reply)"
        st.session_state.history.append(("assistant", reply))
        if result.get("top"):
            st.session_state.top = result["top"]
    st.rerun()
