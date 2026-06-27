from __future__ import annotations

import httpx
import pytest

import frontend.api as api


class _Resp:
    status_code = 200

    def json(self):
        return {"ok": True}


class _FlakyClient:
    calls = 0

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def request(self, *a, **k):
        _FlakyClient.calls += 1
        if _FlakyClient.calls < 3:
            raise httpx.ConnectError("connection refused")
        return _Resp()


def test_call_retries_until_backend_is_up(monkeypatch):
    _FlakyClient.calls = 0
    monkeypatch.setattr(api.httpx, "Client", _FlakyClient)
    monkeypatch.setattr(api.time, "sleep", lambda _s: None)

    assert api.get_config() == {"ok": True}
    assert _FlakyClient.calls == 3


def test_call_gives_up_after_retries(monkeypatch):
    class _Dead(_FlakyClient):
        def request(self, *a, **k):
            raise httpx.ConnectError("refused")

    monkeypatch.setattr(api.httpx, "Client", _Dead)
    monkeypatch.setattr(api.time, "sleep", lambda _s: None)

    with pytest.raises(httpx.ConnectError):
        api.get_config()
