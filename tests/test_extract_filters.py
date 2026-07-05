from __future__ import annotations

from langchain_core.messages import HumanMessage

from valor_auto_agent.graph import nodes


def test_coerce_drops_invalid_and_unknown():
    out = nodes._coerce_filters({"brand": "bmw", "fuel": "petrol", "price_max": 10000, "junk": 1})
    # 'petrol' is not a valid Fuel enum value; 'junk' is not a filter field
    assert out == {"brand": "bmw", "price_max": 10000}


def test_coerce_keeps_valid_enums():
    out = nodes._coerce_filters({"fuel": "diesel", "transmission": "automatica"})
    assert out == {"fuel": "diesel", "transmission": "automatica"}


def test_coerce_skips_empty_values():
    out = nodes._coerce_filters({"brand": "", "model": None, "year_min": 2015})
    assert out == {"year_min": 2015}


async def test_extract_filters_nl_overrides_memory(monkeypatch):
    async def fake_extract(text, model):
        return {"brand": "bmw", "model": "320d", "price_max": 10000}

    monkeypatch.setattr(nodes, "_extract", fake_extract)
    monkeypatch.setattr(
        nodes, "recall_defaults", lambda *a, **k: {"transmission": "manual", "price_max": 5000}
    )

    state = {"messages": [HumanMessage(content="find me a bmw 320d under 10k")]}
    out = await nodes.extract_filters(state)
    pf = out["filters_prefill"]

    assert pf["brand"] == "bmw"
    assert pf["model"] == "320d"
    assert pf["price_max"] == 10000  # nl wins over remembered 5000
    assert pf["transmission"] == "manual"  # gap filled from memory
    assert "read:" in out["prefill_note"]


def test_guess_lang():
    assert nodes._guess_lang("encontra-me um bmw 320d até 10000") == "pt"
    assert nodes._guess_lang("find me a bmw 320d under 10k") == "en"


def test_prefill_note_localized_pt():
    note = nodes._prefill_note({"brand": "bmw"}, {}, {"brand": "bmw"}, "pt")
    assert note.startswith("li:")
    assert "confirma ou ajusta" in note


async def test_extract_filters_threads_language(monkeypatch):
    async def fake_extract(text, model):
        return {"brand": "bmw", "lang": "pt"}

    monkeypatch.setattr(nodes, "_extract", fake_extract)
    monkeypatch.setattr(nodes, "recall_defaults", lambda *a, **k: {})
    out = await nodes.extract_filters({"messages": [HumanMessage(content="quero um bmw")]})
    assert out["lang"] == "pt"
    assert out["prefill_note"].startswith("li:")


async def test_extract_filters_empty_note(monkeypatch):
    async def fake_extract(text, model):
        return {}

    monkeypatch.setattr(nodes, "_extract", fake_extract)
    monkeypatch.setattr(nodes, "recall_defaults", lambda *a, **k: {})

    state = {"messages": [HumanMessage(content="hello there")]}
    out = await nodes.extract_filters(state)
    assert out["filters_prefill"] == {}
    assert "couldn't read" in out["prefill_note"]
