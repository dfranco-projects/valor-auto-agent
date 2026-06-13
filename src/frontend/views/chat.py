from __future__ import annotations

import streamlit as st

from frontend import api
from frontend.components import result_card
from frontend.labels import model_label


def render() -> None:
    st.title("Valor-Auto")

    _, mid, _ = st.columns([1, 5, 1])
    with mid:
        for role, content in st.session_state.history:
            with st.chat_message(role):
                st.markdown(content)

        if st.session_state.pending_filters:
            _filter_form()

        if st.session_state.top:
            st.subheader("Top picks")
            for i, t in enumerate(st.session_state.top, 1):
                result_card(i, t)

    prompt = st.chat_input("Ask the agent — e.g. find me a bmw 320d under 15k")
    if prompt:
        model = st.session_state.rater_model
        if not _provider_ok(model):
            st.error(
                f"No API key configured for {model_label(model)}. "
                "Add the provider key to .env and restart the backend."
            )
            return
        st.session_state.history.append(("user", prompt))
        with st.spinner("Thinking..."):
            res = api.post_search(st.session_state.thread_id, prompt, model)
        _apply(res)
        st.rerun()


def _provider_ok(model: str) -> bool:
    ks = st.session_state.key_status
    return bool(ks.get("gemini") if model.startswith("gemini") else ks.get("anthropic"))


def _apply(res: dict) -> None:
    if res.get("status") == "need_filters":
        st.session_state.pending_filters = True
        st.session_state.filter_schema = res.get("filter_schema")
        st.session_state.history.append(("assistant", res.get("reply") or "filters needed"))
    else:
        st.session_state.pending_filters = False
        st.session_state.history.append(("assistant", res.get("reply") or "done"))
        if res.get("top"):
            st.session_state.top = res["top"]


def _filter_form() -> None:
    st.info("Fill the form below to start the scrape")
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
        if st.form_submit_button("Scrape"):
            values = {
                "brand": brand or None,
                "model": model or None,
                "year_min": int(year_min),
                "year_max": int(year_max),
                "price_min": int(price_min) or None,
                "price_max": int(price_max) or None,
                "km_max": int(km_max) or None,
                "fuel": fuel or None,
                "transmission": transmission or None,
                "location": location or None,
            }
            values = {k: v for k, v in values.items() if v not in (None, "")}
            with st.spinner("Scraping olx + standvirtual and rating..."):
                res = api.post_resume(st.session_state.thread_id, values)
            _apply(res)
            st.rerun()
