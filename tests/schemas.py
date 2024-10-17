import pytest
from eip712.model.input.descriptor import InputEIP712DAppDescriptor

from erc7730.model.input.descriptor import InputERC7730Descriptor
from tests.assertions import assert_model_json_schema
from tests.files import ERC7730_SCHEMA, LEGACY_REGISTRY
from tests.io import load_json_file


def assert_valid_erc_7730(descriptor: InputERC7730Descriptor) -> None:
    """Assert descriptor serializes to a JSON that passes JSON schema validation."""
    assert_model_json_schema(descriptor, ERC7730_SCHEMA)


def assert_valid_legacy_eip_712(descriptor: InputEIP712DAppDescriptor) -> None:
    """Assert descriptor serializes to a JSON that passes JSON schema validation."""
    schema_path = LEGACY_REGISTRY / descriptor.blockchainName / "eip712.schema.json"
    if not schema_path.is_file():
        pytest.skip(f"Legacy registry has no EIP-712 schema for network {descriptor.blockchainName}")
    schema = load_json_file(schema_path)
    assert_model_json_schema(descriptor, schema)
