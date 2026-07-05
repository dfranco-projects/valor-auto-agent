from __future__ import annotations

# user-facing agent messages, localized to the language the user wrote in (en/pt for now).
_MSGS = {
    "en": {
        "couldnt_read": "i couldn't read specific filters — fill the form to start the scrape.",
        "read": "read",
        "from_prefs": "from your usual prefs",
        "confirm": "confirm or adjust below.",
        "no_listings": "no listings matched the filters",
        "found": "found {n} matches — here are the top {k}:",
        "rate_limited": (
            "found {n} listings, but the rater hit its rate limit — showing them unrated for now "
            "(try again in a bit, or pick another model in settings)."
        ),
        "filters_needed": "filters needed — confirm to start the scrape",
        "no_key": "no rater api key is configured — i can only chat once a provider key is set.",
    },
    "pt": {
        "couldnt_read": (
            "não percebi filtros específicos — preenche o formulário para iniciar a pesquisa."
        ),
        "read": "li",
        "from_prefs": "das tuas preferências habituais",
        "confirm": "confirma ou ajusta em baixo.",
        "no_listings": "nenhum anúncio corresponde a estes filtros",
        "found": "encontrei {n} resultados — aqui estão os {k} melhores:",
        "rate_limited": (
            "encontrei {n} anúncios, mas a avaliação atingiu o limite do modelo — a mostrar sem "
            "pontuação por agora (tenta novamente daqui a pouco, ou escolhe outro modelo)."
        ),
        "filters_needed": "preciso dos filtros — confirma para iniciar a pesquisa",
        "no_key": (
            "não há nenhuma chave de api configurada — só posso conversar quando definires uma."
        ),
    },
}

# fallback heuristic for the offline path; the extractor llm returns the language otherwise
_PT_HINTS = (
    "ç", "ã", "õ", "á", "é", " até ", " carro", " quero", " procuro", " barato", " com ", " sob "
)


def _guess_lang(text: str) -> str:
    t = f" {text.lower()} "
    return "pt" if any(h in t for h in _PT_HINTS) else "en"


def _msgs(lang: str | None) -> dict:
    return _MSGS.get((lang or "en")[:2], _MSGS["en"])
