import logging

import pytest

from erc7730.serve.v2 import calldata
from erc7730.serve.v2.model import ConversionFailed, Diagnostic
from tests.files import TEST_RESOURCES
from tests.io import load_json_file
from tests.serve.client import request

pytestmark = pytest.mark.anyio

URL = "/v2/calldata"
USDC = (TEST_RESOURCES / "serve" / "usdc-descriptor.json").read_bytes()


async def test_valid_descriptor_returns_descriptors() -> None:
    response = await request("POST", URL, content=USDC)

    assert response.status_code == 200
    body = response.json()
    expected = load_json_file(TEST_RESOURCES / "serve" / "usdc.json")
    assert sorted(body["descriptors"], key=lambda d: d["selector"]) == expected
    assert body["diagnostics"] == []


async def test_invalid_descriptor_returns_400() -> None:
    response = await request("POST", URL, content=b"{not json")

    assert response.status_code == 400
    body = response.json()
    assert body["descriptors"] == []
    assert [(d["level"], d["title"]) for d in body["diagnostics"]] == [("error", "Invalid descriptor")]


async def test_body_too_large_returns_413() -> None:
    response = await request("POST", URL, content=b" " * (calldata.MAX_BODY_BYTES + 1))

    assert response.status_code == 413
    assert [d["title"] for d in response.json()["diagnostics"]] == ["Body too large"]


async def test_conversion_failure_returns_422_and_is_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    failed = ConversionFailed((Diagnostic(level="error", title="t", message="m"),))
    monkeypatch.setattr(calldata, "compile_json", lambda body: failed)

    response = await request("POST", URL, content=USDC)

    assert response.status_code == 422
    assert response.json() == {"descriptors": [], "diagnostics": [{"level": "error", "title": "t", "message": "m"}]}
    assert any(r.levelno == logging.ERROR and "conversion failed" in r.getMessage() for r in caplog.records)


async def test_unexpected_error_returns_500_and_logs_traceback(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(body: bytes) -> ConversionFailed:
        raise RuntimeError("boom")

    monkeypatch.setattr(calldata, "compile_json", fail)

    response = await request("POST", URL, content=USDC)

    assert response.status_code == 500
    assert response.json() == {"error": "RuntimeError"}
    assert any(r.exc_info is not None and "boom" in str(r.exc_info[1]) for r in caplog.records)
