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
    """Return true for descriptor files, not nested test fixture or signature files."""
    parts = path.relative_to(ERC7730_REGISTRY).parts
    return "tests" not in parts and "testsv2" not in parts and "sigs" not in parts


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
        and path.name
        not in [
            "eip712-DelegatedUserDecryptRequestVerificationV1.json",
            "eip712-UserDecryptRequestVerificationV1.json",
            "eip712-UserDecryptRequestVerificationV2.json",
        ]
    ]
)
ERC7730_DESCRIPTORS = sorted(ERC7730_CALLDATA_DESCRIPTORS + ERC7730_EIP712_DESCRIPTORS)

# Registry descriptors the calldata converter does not support yet (known gaps, reported as conversion errors). They are
# expected to fail: the test turns red once one is fixed, so it can be removed from this list.
ERC7730_EXPECTED_CALLDATA_FAILURES = {
    # visibility conditions on formats other than raw/addressName (#335)
    "gondi/eip712-LoanOffer-v3_1.json",
    "gondi/eip712-LoanOffer-v3_2.json",
    "paraswap/eip712-paraswap.json",
    "permit/eip712-permit-ethereum-dai.json",
    "permit/eip712-permit-polygon-dai.json",
    # constant/value rejected: $.value above 255 or $.base empty
    "rarible/eip712-rarible-exchange-v2.json",
    # visibility condition value not encodable for the field type
    "gondi/eip712-ExecutionData-v3_1.json",
    "gondi/eip712-ExecutionData-v3_2.json",
    "ocarina-trade/eip712-OTCRegistry.json",
}
ERC7730_V2_SCHEMA_PATH = ERC7730_REGISTRY_ROOT / "specs" / "erc7730-v2.schema.json"
ERC7730_V2_SCHEMA = load_json_file(ERC7730_V2_SCHEMA_PATH)

# legacy registry resources
LEGACY_REGISTRY = TEST_REGISTRIES / "ledger-asset-dapps"
LEGACY_EIP712_DESCRIPTORS = sorted(list(LEGACY_REGISTRY.rglob("**/eip712.json")))
