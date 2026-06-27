from __future__ import annotations

from valor_auto_agent.pipeline import _model_match


def test_model_number_token_match():
    # "320d" keeps 3-series 320 variants, drops other models
    assert _model_match("BMW 320 ver d Pack M", "320d")
    assert _model_match("BMW 320d Touring", "320d")
    assert not _model_match("BMW 116 i Confort", "320d")
    assert not _model_match("BMW 318 d LifeStyle", "320d")
    assert not _model_match("BMW i3 60 Ah", "320d")


def test_model_word_match_when_no_number():
    assert _model_match("VW Golf 1.6 TDI", "golf")
    assert not _model_match("VW Polo 1.0", "golf")
