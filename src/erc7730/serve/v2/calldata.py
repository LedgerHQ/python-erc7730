import logging
from dataclasses import asdict
from typing import Any, assert_never

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse

from erc7730.serve.v2.compile import compile_json
from erc7730.serve.v2.model import Compiled, CompileResult, ConversionFailed, Diagnostic, InvalidDescriptor

MAX_BODY_BYTES = 1024 * 1024

logger = logging.getLogger(__name__)


async def calldata(request: Request) -> JSONResponse:
    body = await _read_body(request, MAX_BODY_BYTES)
    if body is None:
        message = f"the body is over {MAX_BODY_BYTES} bytes"
        return _response(413, (), (Diagnostic(level="error", title="Body too large", message=message),))
    try:
        result = await run_in_threadpool(compile_json, body)
    except Exception as e:
        logger.exception("unexpected error while compiling calldata descriptors")
        return JSONResponse({"error": type(e).__name__}, status_code=500)
    if isinstance(result, ConversionFailed):
        logger.error("calldata conversion failed: %s", result.diagnostics)
    return to_response(result)


def to_response(result: CompileResult) -> JSONResponse:
    match result:
        case Compiled(descriptors, diagnostics):
            return _response(200, descriptors, diagnostics)
        case ConversionFailed(diagnostics):
            return _response(422, (), diagnostics)
        case InvalidDescriptor(message):
            return _response(400, (), (Diagnostic(level="error", title="Invalid descriptor", message=message),))
        case _:
            assert_never(result)


async def _read_body(request: Request, limit: int) -> bytes | None:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            return None
    return bytes(body)


def _response(
    status_code: int, descriptors: tuple[dict[str, Any], ...], diagnostics: tuple[Diagnostic, ...]
) -> JSONResponse:
    body = {"descriptors": list(descriptors), "diagnostics": [asdict(d) for d in diagnostics]}
    return JSONResponse(body, status_code=status_code)
