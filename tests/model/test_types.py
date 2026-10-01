import pytest
from pydantic import TypeAdapter, ValidationError

from erc7730.model.input.v2.context import InputDeployment
from erc7730.model.types import MixedCaseAddress

CHECKSUMMED = "0xb426b5AE61c23fF1B901a8AD1f1A3921D1E9D2F1"
WRONG_CHECKSUM = "0xb426B5aE61c23Ff1b901A8ad1F1A3921D1E9D2f1"
UPPERCASE = "0x" + CHECKSUMMED[2:].upper()


@pytest.mark.parametrize(
    "address",
    [
        CHECKSUMMED,
        CHECKSUMMED.lower(),
        "0x0000000000000000000000000000000000000000",
        "0x1234567890123456789012345678901234567890",
    ],
)
def test_mixed_case_address_accepted(address: str) -> None:
    assert TypeAdapter(MixedCaseAddress).validate_python(address) == address


@pytest.mark.parametrize("address", [WRONG_CHECKSUM, UPPERCASE])
def test_mixed_case_address_wrong_checksum(address: str) -> None:
    with pytest.raises(ValidationError) as e:
        TypeAdapter(MixedCaseAddress).validate_python(address)
    message = e.value.errors()[0]["msg"]
    assert "invalid EIP-55 checksum" in message
    assert address in message
    assert CHECKSUMMED in message


@pytest.mark.parametrize(
    "address",
    [
        "0xb426",
        "b426b5AE61c23fF1B901a8AD1f1A3921D1E9D2F1",
        "0xZZ26b5AE61c23fF1B901a8AD1f1A3921D1E9D2F1",
        CHECKSUMMED.lower() + "\n",
    ],
)
def test_mixed_case_address_wrong_shape(address: str) -> None:
    with pytest.raises(ValidationError) as e:
        TypeAdapter(MixedCaseAddress).validate_python(address)
    assert "expected a 20 bytes, hexadecimal Ethereum address" in e.value.errors()[0]["msg"]


def test_deployment_wrong_checksum() -> None:
    with pytest.raises(ValidationError, match="invalid EIP-55 checksum"):
        InputDeployment(chainId=1, address=WRONG_CHECKSUM)
