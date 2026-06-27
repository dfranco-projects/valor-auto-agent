from __future__ import annotations

import streamlit as st

from frontend import api
from frontend.components import result_card
from frontend.labels import BRAND_SLUGS, brand_label, model_label

_FUELS = ["", "gasolina", "diesel", "hibrido", "eletrico", "gpl"]
_TRANS = ["", "manual", "automatica"]


def render() -> None:
    st.title("Valor-Auto")

    _, mid, _ = st.columns([1, 5, 1])
    with mid:
        _render_history()

        if st.session_state.pending_filters:
            _filter_form()

        if st.session_state.top:
            st.subheader("Top picks")
            for i, t in enumerate(st.session_state.top, 1):
                result_card(i, t)

        _edit_box()

    prompt = st.chat_input("Ask the agent — e.g. find me a bmw 320d under 15k")
    if prompt:
        _submit(prompt)


def _render_history() -> None:
    for i, (role, content) in enumerate(st.session_state.history):
        if role == "error":
            with st.chat_message("assistant"):
                st.error(content)
            continue
        with st.chat_message(role):
            st.markdown(content)
            if role == "user":
                _msg_actions(i)


def _msg_actions(i: int) -> None:
    # hidden by default, revealed on message hover via css (.st-key-msgact-*)
    with st.container(key=f"msgact-{i}"):
        c1, c2, _ = st.columns([1, 1, 8])
        if c1.button("✏️", key=f"edit-{i}", help="Edit & re-prompt"):
            st.session_state.editing = i
            st.rerun()
        if c2.button("🗑️", key=f"cancel-{i}", help="Cancel this message"):
            _drop_turn(i)
            st.rerun()


def _drop_turn(i: int) -> None:
    # remove the user message at i plus its responses (up to the next user message)
    hist = st.session_state.history
    j = i + 1
    while j < len(hist) and hist[j][0] != "user":
        j += 1
    del hist[i:j]


def _edit_box() -> None:
    i = st.session_state.get("editing")
    if i is None or i >= len(st.session_state.history):
        st.session_state.editing = None
        return
    with st.container(border=True):
        st.caption("Edit & re-prompt")
        new = st.text_area(
            "edit",
            value=st.session_state.history[i][1],
            key="edit_text",
            label_visibility="collapsed",
        )
        c1, c2, _ = st.columns([1, 1, 6])
        if c1.button("Resend", type="primary"):
            _drop_turn(i)
            st.session_state.editing = None
            _submit(new)
        if c2.button("Discard"):
            st.session_state.editing = None
            st.rerun()


def _submit(prompt: str) -> None:
    prompt = (prompt or "").strip()
    if not prompt:
        return
    model = st.session_state.rater_model
    st.session_state.history.append(("user", prompt))

    if not _provider_ok(model):
        st.session_state.history.append(
            (
                "error",
                f"No API key configured for {model_label(model)}. "
                "Add the provider key to .env and restart the backend.",
            )
        )
        st.rerun()

    try:
        with st.spinner("Thinking..."):
            res = api.post_search(st.session_state.thread_id, prompt, model)
    except Exception as e:  # surface backend/connection failures instead of crashing
        st.session_state.history.append(("error", f"Something went wrong: {e}"))
        st.rerun()

    _apply(res)
    st.rerun()


def _provider_ok(model: str) -> bool:
    ks = st.session_state.key_status
    return bool(ks.get("gemini") if model.startswith("gemini") else ks.get("anthropic"))


def _apply(res: dict) -> None:
    if res.get("status") == "need_filters":
        st.session_state.pending_filters = True
        st.session_state.filter_schema = res.get("filter_schema")
        # seed the form from the agent's nl extraction + remembered prefs (pre-filled to confirm)
        st.session_state.last_filters = res.get("prefill") or None
        st.session_state.history.append(("assistant", res.get("reply") or "filters needed"))
    else:
        st.session_state.pending_filters = False
        st.session_state.history.append(("assistant", res.get("reply") or "done"))
        if res.get("top"):
            st.session_state.top = res["top"]


def _idx(options: list[str], value, default: int = 0) -> int:
    return options.index(value) if value in options else default


def _filter_form() -> None:
    prev = st.session_state.get("last_filters") or {}
    st.info("Confirm or adjust the pre-filled filters below, then scrape")
    with st.form("filters"):
        c1, c2 = st.columns(2)
        with c1:
            brand = st.selectbox(
                "brand",
                BRAND_SLUGS,
                index=_idx(BRAND_SLUGS, prev.get("brand")),
                format_func=brand_label,
            )
            model = st.text_input("model", prev.get("model", ""))
            year_min = st.number_input("year min", 1980, 2026, int(prev.get("year_min", 2015)))
            year_max = st.number_input("year max", 1980, 2026, int(prev.get("year_max", 2024)))
            km_max = st.number_input(
                "km max", 0, 500000, int(prev.get("km_max", 200000)), step=5000
            )
        with c2:
            price_min = st.number_input(
                "price min €", 0, 200000, int(prev.get("price_min", 0)), step=500
            )
            price_max = st.number_input(
                "price max €", 0, 200000, int(prev.get("price_max", 20000)), step=500
            )
            fuel = st.selectbox("fuel", _FUELS, index=_idx(_FUELS, prev.get("fuel")))
            transmission = st.selectbox(
                "transmission", _TRANS, index=_idx(_TRANS, prev.get("transmission"))
            )
            location = st.text_input("location", prev.get("location", ""))
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
            st.session_state.last_filters = values
            try:
                with st.spinner("Scraping olx + standvirtual and rating..."):
                    res = api.post_resume(st.session_state.thread_id, values)
            except Exception as e:
                st.session_state.history.append(("error", f"Scrape failed: {e}"))
                st.rerun()  # keep the form (pending_filters stays True) with the entered values
            if res.get("status") == "done" and not res.get("top"):
                st.session_state.history.append(
                    ("error", "No listings matched these filters — adjust them and try again.")
                )
                st.rerun()  # re-show the pre-filled form
            _apply(res)
            st.rerun()
