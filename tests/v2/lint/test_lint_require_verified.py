from collections.abc import Callable

import pytest

from erc7730.common import client
from erc7730.common.output import ListOutputAdder, Output
from erc7730.model.abi import ABI
from tests.v2.lint.conftest import LintDescriptor

NOT_VERIFIED = client.ContractNotVerifiedError("contract 0x1 on chain 1 is not verified on Sourcify")
IMPLEMENTATION_NOT_VERIFIED = client.ProxyImplementationNotVerifiedError("contract 0x1 on chain 1 is a proxy")
CHAIN_NOT_SUPPORTED = client.ChainNotSupportedError("chain 1 is not supported by Sourcify")
RATE_LIMITED = Exception("Sourcify rate limit exceeded, please retry")


def raising(error: Exception) -> Callable[[int], list[ABI]]:
    def abis_of(chain_id: int) -> list[ABI]:
        raise error

    return abis_of


def level_of(out: ListOutputAdder, title: str) -> Output.Level:
    return next(output.level for output in out.outputs if output.title == title)


@pytest.mark.parametrize(
    ("error", "title", "default_level"),
    [
        (NOT_VERIFIED, "Contract not verified", Output.Level.WARNING),
        (IMPLEMENTATION_NOT_VERIFIED, "Proxy implementation not verified", Output.Level.WARNING),
        (CHAIN_NOT_SUPPORTED, "Chain not supported", Output.Level.INFO),
    ],
)
def test_unverified_contract_is_an_error_only_when_required(
    lint_descriptor: LintDescriptor, error: Exception, title: str, default_level: Output.Level
) -> None:
    out = lint_descriptor(raising(error), False)
    assert level_of(out, title) == default_level
    assert not out.has_errors

    out = lint_descriptor(raising(error), True)
    assert level_of(out, title) == Output.Level.ERROR
    assert out.has_errors


def test_fetch_failure_is_an_error_only_when_verified_is_required(lint_descriptor: LintDescriptor) -> None:
    out = lint_descriptor(raising(RATE_LIMITED), False)
    assert level_of(out, "Could not fetch ABI") == Output.Level.WARNING
    assert not out.has_errors

    out = lint_descriptor(raising(RATE_LIMITED), True)
    assert level_of(out, "Could not fetch ABI") == Output.Level.ERROR
    assert out.has_errors
