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
ERC7730_CALLDATA_DESCRIPTORS = sorted(list(ERC7730_REGISTRY.rglob(f"{ERC_7730_REGISTRY_CALLDATA_PREFIX}*.json")))
ERC7730_EIP712_DESCRIPTORS = sorted(list(ERC7730_REGISTRY.rglob(f"{ERC_7730_REGISTRY_EIP712_PREFIX}*.json")))
ERC7730_DESCRIPTORS = sorted(ERC7730_CALLDATA_DESCRIPTORS + ERC7730_EIP712_DESCRIPTORS)
ERC7730_SCHEMA_PATH = ERC7730_REGISTRY_ROOT / "specs" / "erc7730-v1.schema.json"
ERC7730_SCHEMA = load_json_file(ERC7730_SCHEMA_PATH)

# legacy registry resources
LEGACY_REGISTRY = TEST_REGISTRIES / "ledger-asset-dapps"
LEGACY_EIP712_DESCRIPTORS = sorted(list(LEGACY_REGISTRY.rglob("**/eip712.json")))
