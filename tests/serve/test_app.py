from typing import Any

import pytest

from erc7730.serve import app
from tests.serve.client import request


@pytest.mark.anyio
async def test_health() -> None:
    response = await request("GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_serve_limits_concurrent_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(app.uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))

    app.serve("127.0.0.1", 8730)

    assert calls[0]["limit_concurrency"] == app.MAX_CONCURRENT_REQUESTS
