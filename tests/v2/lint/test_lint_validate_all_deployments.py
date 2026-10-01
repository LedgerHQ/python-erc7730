from erc7730.common import client
from erc7730.common.abi import parse_signature
from erc7730.common.output import ListOutputAdder
from erc7730.model.abi import ABI
from tests.v2.lint.conftest import LintDescriptor

# the functions the descriptor declares formats for
TRANSFER = parse_signature("transfer(address _to, uint256 _value)")
APPROVE = parse_signature("approve(address _spender, uint256 _value)")
# same functions with different parameter names, so display field paths do not match
TRANSFER_RENAMED = parse_signature("transfer(address to, uint256 value)")
APPROVE_RENAMED = parse_signature("approve(address spender, uint256 value)")


def titles(out: ListOutputAdder, title: str) -> int:
    return sum(1 for output in out.outputs if output.title == title)


def test_deployments_with_the_same_abi_are_validated_once(lint_descriptor: LintDescriptor) -> None:
    out = lint_descriptor(lambda chain_id: [TRANSFER, APPROVE], False)
    assert titles(out, "Deployment ABIs differ") == 0
    assert titles(out, "Invalid display field") == 0


def test_deployments_with_different_abis_are_reported_and_each_validated(lint_descriptor: LintDescriptor) -> None:
    def abis_of(chain_id: int) -> list[ABI]:
        return [TRANSFER, APPROVE] if chain_id == 1 else [TRANSFER_RENAMED, APPROVE_RENAMED]

    out = lint_descriptor(abis_of, False)
    assert titles(out, "Deployment ABIs differ") == 1
    # the chain 137 ABI names the parameters differently, so the 4 display fields are invalid against it only
    assert titles(out, "Invalid display field") == 4


def test_a_deployment_that_cannot_be_fetched_does_not_stop_the_others(lint_descriptor: LintDescriptor) -> None:
    def abis_of(chain_id: int) -> list[ABI]:
        if chain_id == 1:
            raise client.ContractNotVerifiedError("contract 0x1 on chain 1 is not verified on Sourcify")
        return [TRANSFER_RENAMED, APPROVE_RENAMED]

    out = lint_descriptor(abis_of, False)
    assert titles(out, "Contract not verified") == 1
    assert titles(out, "Deployment ABIs differ") == 0
    assert titles(out, "Invalid display field") == 4
