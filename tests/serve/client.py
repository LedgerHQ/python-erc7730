from typing import Any

import httpx

from erc7730.serve.app import app


async def request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, url, **kwargs)
