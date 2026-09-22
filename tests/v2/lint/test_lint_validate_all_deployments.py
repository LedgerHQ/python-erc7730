from collections.abc import Callable

import pytest

from erc7730.common import client
from erc7730.common.abi import parse_signature
from erc7730.common.output import ListOutputAdder
from erc7730.lint.v2.lint import lint_all
from erc7730.model.abi import ABI
from tests.files import ERC7730_REGISTRY

# USDT is deployed on chains 1 and 137, and declares formats for transfer and approve
USDT = ERC7730_REGISTRY / "tether" / "calldata-usdt.json"

TRANSFER = parse_signature("transfer(address _to, uint256 _value)")
APPROVE = parse_signature("approve(address _spender, uint256 _value)")
# same functions with different parameter names, so display field paths do not match
TRANSFER_RENAMED = parse_signature("transfer(address to, uint256 value)")
APPROVE_RENAMED = parse_signature("approve(address spender, uint256 value)")


def lint_with(monkeypatch: pytest.MonkeyPatch, abis_of: Callable[[int], list[ABI]]) -> ListOutputAdder:
    monkeypatch.setattr(client, "get_contract_abis", lambda chain_id, contract_address: abis_of(chain_id))
    out = ListOutputAdder()
    lint_all([USDT], out)
    return out


def titles(out: ListOutputAdder, title: str) -> int:
    return sum(1 for output in out.outputs if output.title == title)


def test_deployments_with_the_same_abi_are_validated_once(monkeypatch: pytest.MonkeyPatch) -> None:
    out = lint_with(monkeypatch, lambda chain_id: [TRANSFER, APPROVE])
    assert titles(out, "Deployment ABIs differ") == 0
    assert titles(out, "Invalid display field") == 0


def test_deployments_with_different_abis_are_reported_and_each_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    out = lint_with(
        monkeypatch, lambda chain_id: [TRANSFER, APPROVE] if chain_id == 1 else [TRANSFER_RENAMED, APPROVE_RENAMED]
    )
    assert titles(out, "Deployment ABIs differ") == 1
    # the chain 137 ABI names the parameters differently, so the 4 display fields are invalid against it only
    assert titles(out, "Invalid display field") == 4


def test_a_deployment_that_cannot_be_fetched_does_not_stop_the_others(monkeypatch: pytest.MonkeyPatch) -> None:
    def abis_of(chain_id: int) -> list[ABI]:
        if chain_id == 1:
            raise client.ContractNotVerifiedError("contract 0x1 on chain 1 is not verified on Sourcify")
        return [TRANSFER_RENAMED, APPROVE_RENAMED]

    out = lint_with(monkeypatch, abis_of)
    assert titles(out, "Contract not verified") == 1
    assert titles(out, "Deployment ABIs differ") == 0
    assert titles(out, "Invalid display field") == 4
