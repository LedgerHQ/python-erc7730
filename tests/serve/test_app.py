import pytest

from tests.serve.client import request

pytestmark = pytest.mark.anyio


async def test_health() -> None:
    response = await request("GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
