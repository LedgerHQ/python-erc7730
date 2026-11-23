import logging

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from erc7730.serve.v2.calldata import calldata

MAX_CONCURRENT_REQUESTS = 32


# async so that it answers on the event loop even when compiles fill the thread pool
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/v2/calldata", calldata, methods=["POST"]),
    ]
)


def serve(host: str, port: int) -> None:
    logging.basicConfig(format="%(levelname)s [%(asctime)s] %(name)s - %(message)s", level=logging.INFO)
    uvicorn.run(app, host=host, port=port, access_log=False, limit_concurrency=MAX_CONCURRENT_REQUESTS)
