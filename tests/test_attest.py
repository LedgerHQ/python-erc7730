import json
import json
from datetime import datetime, timezone
from pathlib import Path

from eth_abi import decode
from typer.testing import CliRunner

from erc7730.attest import (
    ATTEST_SELECTOR,
    build_eas_attest_tx,
    build_eas_typed_data,
    descriptor_hash,
    load_descriptor_json,
)
from erc7730.main import app

runner = CliRunner()


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value))


def test_descriptor_hash_resolves_includes_first(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    child = tmp_path / "child.json"

    _write_json(base, {"b": 2, "a": 1})
    _write_json(child, {"includes": "base.json", "c": 3})

    loaded = load_descriptor_json(child)
    assert loaded == {"a": 1, "b": 2, "c": 3}
    assert descriptor_hash(loaded) == descriptor_hash({"a": 1, "b": 2, "c": 3})


def test_build_eas_typed_data() -> None:
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    salt = b"\x11" * 32
    payload = build_eas_typed_data("0x" + "22" * 32, ttl="6mo", now=now, salt=salt)

    assert payload["primaryType"] == "Attest"
    assert payload["domain"] == {
        "name": "EAS Attestation",
        "version": "0.26",
        "chainId": "1",
        "verifyingContract": "0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587",
    }
    assert payload["message"]["revocable"] is True
    assert payload["message"]["salt"] == "0x" + salt.hex()
    assert payload["message"]["time"] == str(int(now.timestamp()))
    assert payload["message"]["expirationTime"] == str(int(datetime(2026, 7, 2, 3, 4, 5, tzinfo=timezone.utc).timestamp()))


def test_build_eas_attest_tx() -> None:
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    digest = "0x" + "33" * 32
    tx = build_eas_attest_tx(digest, ttl="30d", now=now)

    assert tx["to"] == "0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587"
    assert tx["value"] == "0x0"
    assert tx["chainId"] == "0x1"
    assert tx["data"].startswith("0x" + ATTEST_SELECTOR.hex())
    schema_uid, attestation = decode(
        ["bytes32", "(address,uint64,bool,bytes32,bytes,uint256)"],
        bytes.fromhex(tx["data"][2 + len(ATTEST_SELECTOR.hex()) :]),
    )
    assert schema_uid.hex() == "e023eef113c1670774801c34b377fdf612dd8a4d2fa92fe382e15bd91fafb5c2"
    assert attestation[4] == bytes.fromhex(digest.removeprefix("0x"))
    assert len(attestation[4]) == 32


def test_cli_attest_eip712(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    child = tmp_path / "child.json"

    _write_json(base, {"b": 2, "a": 1})
    _write_json(child, {"includes": "base.json", "c": 3})

    result = runner.invoke(app, ["attest", str(child)])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["primaryType"] == "Attest"
    assert payload["message"]["data"] == descriptor_hash({"a": 1, "b": 2, "c": 3})
    assert payload["message"]["revocable"] is True
    assert len(payload["message"]["salt"]) == 66


def test_cli_attest_tx(tmp_path: Path) -> None:
    descriptor = tmp_path / "descriptor.json"
    _write_json(descriptor, {"a": 1})

    result = runner.invoke(app, ["attest", "--format", "tx", str(descriptor)])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert set(payload) == {"to", "value", "data", "chainId"}
    assert payload["to"] == "0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587"
    assert payload["value"] == "0x0"
    assert payload["chainId"] == "0x1"
    assert payload["data"].startswith("0x" + ATTEST_SELECTOR.hex())
