import json
from typing import Any

from eth_utils import keccak

from erc7730.common.output import ListOutputAdder
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.lint.v2.lint_validate_eip712_domain_separator import ValidateEIP712DomainSeparatorLinter
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

PERMIT_TYPE = "Permit(address owner,uint256 value)"
CONTRACT = "0x000000000000000000000000000000000000dEaD"


def _separator(*members: tuple[str, str, bytes]) -> str:
    domain_type = "EIP712Domain(" + ",".join(f"{t} {n}" for t, n, _ in members) + ")"
    return "0x" + keccak(keccak(text=domain_type) + b"".join(v for _, _, v in members)).hex()


NAME = ("string", "name", keccak(text="Test"))
SALT = ("bytes32", "salt", bytes.fromhex("11" * 32))
NAME_ONLY = _separator(NAME)


def lint(eip712: dict[str, Any]) -> list[tuple[str | None, str]]:
    descriptor = InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": {"$id": "test", "eip712": eip712},
                "metadata": {"owner": "Test Owner"},
                "display": {
                    "formats": {
                        PERMIT_TYPE: {"intent": "Test", "fields": [{"path": "value", "label": "V", "format": "raw"}]}
                    }
                },
            }
        )
    )
    out = ListOutputAdder()
    resolved = ERC7730InputToResolved().convert(descriptor, out)
    assert resolved is not None, out.outputs
    ValidateEIP712DomainSeparatorLinter().lint(descriptor, resolved, out)
    return [(o.title, o.message) for o in out.outputs]


def test_no_domain_separator() -> None:
    assert lint({"deployments": [{"chainId": 1, "address": CONTRACT}], "domain": {"name": "Test"}}) == []


def test_matching_domain_separator_without_deployment() -> None:
    assert lint({"domain": {"name": "Test"}, "domainSeparator": NAME_ONLY}) == []


def test_matching_domain_separator_with_salt() -> None:
    separator = _separator(NAME, SALT)
    assert lint({"domain": {"name": "Test", "salt": "0x" + "11" * 32}, "domainSeparator": separator}) == []


def test_matching_domain_separator_from_the_domain_chain_and_contract() -> None:
    separator = _separator(
        NAME,
        ("uint256", "chainId", (1).to_bytes(32)),
        ("address", "verifyingContract", bytes.fromhex(CONTRACT[2:]).rjust(32, b"\x00")),
    )
    domain = {"name": "Test", "chainId": 1, "verifyingContract": CONTRACT}
    assert lint({"domain": domain, "domainSeparator": separator}) == []


def test_matching_domain_separator_of_a_deployment() -> None:
    separator = _separator(
        NAME,
        ("uint256", "chainId", (1).to_bytes(32)),
        ("address", "verifyingContract", bytes.fromhex(CONTRACT[2:]).rjust(32, b"\x00")),
    )
    assert (
        lint(
            {
                "domain": {"name": "Test"},
                "deployments": [{"chainId": 1, "address": CONTRACT}],
                "domainSeparator": separator,
            }
        )
        == []
    )


def test_domain_separator_mismatch() -> None:
    outputs = lint({"domain": {"name": "Test"}, "domainSeparator": "0x" + "ab" * 32})
    assert [title for title, _ in outputs] == ["Domain separator mismatch"]
    assert NAME_ONLY in outputs[0][1]


def test_domain_separator_matching_only_some_deployments() -> None:
    separator = _separator(
        NAME,
        ("uint256", "chainId", (1).to_bytes(32)),
        ("address", "verifyingContract", bytes.fromhex(CONTRACT[2:]).rjust(32, b"\x00")),
    )
    outputs = lint(
        {
            "domain": {"name": "Test"},
            "deployments": [{"chainId": 1, "address": CONTRACT}, {"chainId": 10, "address": CONTRACT}],
            "domainSeparator": separator,
        }
    )
    assert [title for title, _ in outputs] == ["Domain separator shared by several deployments"]


def test_invalid_domain_separator_length() -> None:
    outputs = lint({"domain": {"name": "Test"}, "domainSeparator": "0x1234"})
    assert [title for title, _ in outputs] == ["Invalid domain separator"]


def test_domain_separator_without_domain_is_a_mismatch() -> None:
    outputs = lint({"domainSeparator": "0x" + "ab" * 32})
    assert [title for title, _ in outputs] == ["Domain separator mismatch"]
