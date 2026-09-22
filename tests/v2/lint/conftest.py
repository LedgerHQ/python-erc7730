from collections.abc import Callable

import pytest

from erc7730.common import client
from erc7730.common.output import ListOutputAdder
from erc7730.lint.v2.lint import lint_all
from erc7730.model.abi import ABI
from tests.files import TEST_RESOURCES

# a descriptor with deployments on chains 1 and 137, and formats for transfer and approve with named parameters
TWO_DEPLOYMENTS = TEST_RESOURCES / "lint" / "calldata-two-deployments.json"

LintDescriptor = Callable[[Callable[[int], list[ABI]], bool], ListOutputAdder]


@pytest.fixture
def lint_descriptor(monkeypatch: pytest.MonkeyPatch) -> LintDescriptor:
    """Lint the two deployments descriptor, with reference ABIs (or failures) provided per chain id."""

    def lint(abis_of: Callable[[int], list[ABI]], require_verified: bool = False) -> ListOutputAdder:
        monkeypatch.setattr(client, "get_contract_abis", lambda chain_id, contract_address: abis_of(chain_id))
        out = ListOutputAdder()
        lint_all([TWO_DEPLOYMENTS], out, require_verified=require_verified)
        return out

    return lint
