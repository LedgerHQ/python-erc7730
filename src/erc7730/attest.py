from __future__ import annotations

import json
import os
import re
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from eth_abi import encode
from eth_utils import keccak
from eth_utils.abi import function_signature_to_4byte_selector
import jcs

from erc7730.common.json import read_json_with_includes

EAS_SCHEMA_UID = "0xe023eef113c1670774801c34b377fdf612dd8a4d2fa92fe382e15bd91fafb5c2"
EAS_CONTRACT_ADDRESS = "0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587"
EAS_DOMAIN_NAME = "EAS Attestation"
EAS_DOMAIN_VERSION = "0.26"
EAS_ATTEST_VERSION = 2
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_BYTES32 = "0x" + "00" * 32
ATTEST_SIGNATURE = "attest((bytes32,(address,uint64,bool,bytes32,bytes,uint256)))"
ATTEST_SELECTOR = function_signature_to_4byte_selector(ATTEST_SIGNATURE)

_TTL_RE = re.compile(r"^(\d+)(mo|[smhdwy])$")


def load_descriptor_json(path: Path) -> dict[str, Any]:
    """Load a descriptor JSON file, resolving includes first."""
    value = read_json_with_includes(path)
    if not isinstance(value, dict):
        raise ValueError("descriptor must be a JSON object")
    return value


def canonical_json(value: Any) -> str:
    """Serialize JSON using deterministic key ordering and compact separators."""
    return jcs.canonicalize(value).decode()


def descriptor_hash(descriptor: dict[str, Any]) -> str:
    """Compute the ERC-8176 descriptor hash."""
    return "0x" + keccak(text=canonical_json(descriptor)).hex()


def _add_months(value: datetime, months: int) -> datetime:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _hex_bytes32(value: str) -> bytes:
    return bytes.fromhex(value.removeprefix("0x"))


def _hex_bytes(value: str) -> bytes:
    return bytes.fromhex(value.removeprefix("0x"))


def build_eas_attestation_message(
    descriptor_digest: str,
    *,
    expiration_time: datetime,
    now: datetime | None = None,
    salt: bytes | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    salt_bytes = salt if salt is not None else os.urandom(32)
    return {
        "version": EAS_ATTEST_VERSION,
        "schema": EAS_SCHEMA_UID,
        "recipient": ZERO_ADDRESS,
        "time": str(int(now.timestamp())),
        "expirationTime": str(int(expiration_time.timestamp())),
        "revocable": True,
        "refUID": ZERO_BYTES32,
        "data": descriptor_digest,
        "salt": "0x" + salt_bytes.hex(),
    }


def build_eas_typed_data(
    descriptor_digest: str,
    *,
    ttl: str = "6mo",
    now: datetime | None = None,
    salt: bytes | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    expiration_time = _apply_ttl(now, ttl)
    message = build_eas_attestation_message(
        descriptor_digest,
        expiration_time=expiration_time,
        now=now,
        salt=salt,
    )
    return {
        "domain": {
            "name": EAS_DOMAIN_NAME,
            "version": EAS_DOMAIN_VERSION,
            "chainId": "1",
            "verifyingContract": EAS_CONTRACT_ADDRESS,
        },
        "primaryType": "Attest",
        "types": {
            "Attest": [
                {"name": "version", "type": "uint16"},
                {"name": "schema", "type": "bytes32"},
                {"name": "recipient", "type": "address"},
                {"name": "time", "type": "uint64"},
                {"name": "expirationTime", "type": "uint64"},
                {"name": "revocable", "type": "bool"},
                {"name": "refUID", "type": "bytes32"},
                {"name": "data", "type": "bytes"},
                {"name": "salt", "type": "bytes32"},
            ]
        },
        "message": message,
    }


def _apply_ttl(now: datetime, ttl: str) -> datetime:
    match = _TTL_RE.fullmatch(ttl.strip())
    if match is None:
        raise ValueError("ttl must look like 30d, 6mo, 12h, 15m, or 90s")

    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "mo":
        return _add_months(now, amount)
    if unit == "y":
        return _add_months(now, amount * 12)

    delta_by_unit: dict[str, timedelta] = {
        "s": timedelta(seconds=amount),
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount),
    }
    return now + delta_by_unit[unit]


def build_eas_attest_tx(descriptor_digest: str, *, ttl: str = "6mo", now: datetime | None = None) -> dict[str, str]:
    now = now or datetime.now(timezone.utc)
    expiration_time = _apply_ttl(now, ttl)
    calldata = encode(
        ["bytes32", "(address,uint64,bool,bytes32,bytes,uint256)"],
        [
            _hex_bytes32(EAS_SCHEMA_UID),
            (
                ZERO_ADDRESS,
                int(expiration_time.timestamp()),
                True,
                _hex_bytes32(ZERO_BYTES32),
                _hex_bytes(descriptor_digest),
                0,
            ),
        ],
    )
    return {
        "to": EAS_CONTRACT_ADDRESS,
        "value": "0x0",
        "data": "0x" + ATTEST_SELECTOR.hex() + calldata.hex(),
        "chainId": "0x1",
    }
