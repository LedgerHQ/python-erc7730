from os import getcwd
from pathlib import Path

from erc7730 import (
    ERC_7730_REGISTRY_CALLDATA_PREFIX,
    ERC_7730_REGISTRY_DIRECTORY,
    ERC_7730_REGISTRY_EIP712_PREFIX,
)
from tests.io import load_json_file

# project root directory
PROJECT_ROOT = Path(getcwd())
while not (PROJECT_ROOT / "pyproject.toml").is_file():
    PROJECT_ROOT = PROJECT_ROOT.parent

# test resources
TEST_RESOURCES = PROJECT_ROOT / "tests" / "resources"
TEST_REGISTRIES = PROJECT_ROOT / "tests" / "registries"

# ERC-7730 registry resources
ERC7730_REGISTRY_ROOT = TEST_REGISTRIES / "clear-signing-erc7730-registry"
ERC7730_REGISTRY = ERC7730_REGISTRY_ROOT / ERC_7730_REGISTRY_DIRECTORY


def _is_registry_descriptor(path: Path) -> bool:
    """Return true for descriptor files, not nested test fixture files."""
    return (
        "tests" not in path.relative_to(ERC7730_REGISTRY).parts
        and "testsv2" not in path.relative_to(ERC7730_REGISTRY).parts
    )


ERC7730_CALLDATA_DESCRIPTORS = sorted(
    [
        path
        for path in ERC7730_REGISTRY.rglob(f"{ERC_7730_REGISTRY_CALLDATA_PREFIX}*.json")
        if _is_registry_descriptor(path)
    ]
)
ERC7730_EIP712_DESCRIPTORS = sorted(
    [
        path
        for path in ERC7730_REGISTRY.rglob(f"{ERC_7730_REGISTRY_EIP712_PREFIX}*.json")
        if _is_registry_descriptor(path)
    ]
)
ERC7730_DESCRIPTORS = sorted(ERC7730_CALLDATA_DESCRIPTORS + ERC7730_EIP712_DESCRIPTORS)

# Registry descriptors that legitimately generate no calldata descriptor: conversion is still run on them (exercising
# resolution), but the non-empty calldata assertion is skipped.
ERC7730_EXPECTED_EMPTY_CALLDATA = {
    "calldata-KasExitBridge.json",  # only deployed on chain 38833 (Igra), which is not a Ledger-supported network
    "calldata-PftNft.json",  # enum keyed by "True"/"False" instead of integer field values (not encodable as uint8)
}
ERC7730_V2_SCHEMA_PATH = ERC7730_REGISTRY_ROOT / "specs" / "erc7730-v2.schema.json"
ERC7730_V2_SCHEMA = load_json_file(ERC7730_V2_SCHEMA_PATH)

# legacy registry resources
LEGACY_REGISTRY = TEST_REGISTRIES / "ledger-asset-dapps"
LEGACY_EIP712_DESCRIPTORS = sorted(list(LEGACY_REGISTRY.rglob("**/eip712.json")))
