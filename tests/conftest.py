from __future__ import annotations

import pytest

from valor_auto_agent import config


@pytest.fixture(autouse=True)
def _fresh_settings():
    # config.load() is lru_cached; tests set VALOR_* env vars per-test and expect fresh loads
    config.load.cache_clear()
    yield
    config.load.cache_clear()
