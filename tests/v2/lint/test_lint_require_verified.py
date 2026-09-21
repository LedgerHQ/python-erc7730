import pytest

from erc7730.common import client
from erc7730.common.output import ListOutputAdder, Output
from erc7730.lint.v2.lint import lint_all
from tests.files import ERC7730_REGISTRY

USDT = ERC7730_REGISTRY / "tether" / "calldata-usdt.json"

NOT_VERIFIED = client.ContractNotVerifiedError("contract 0x1 on chain 1 is not verified on Sourcify")
IMPLEMENTATION_NOT_VERIFIED = client.ProxyImplementationNotVerifiedError("contract 0x1 on chain 1 is a proxy")
CHAIN_NOT_SUPPORTED = client.ChainNotSupportedError("chain 1 is not supported by Sourcify")
RATE_LIMITED = Exception("Sourcify rate limit exceeded, please retry")


def lint_with(monkeypatch: pytest.MonkeyPatch, error: Exception, require_verified: bool) -> ListOutputAdder:
    def get_contract_abis(chain_id: int, contract_address: str) -> list[object]:
        raise error

    monkeypatch.setattr(client, "get_contract_abis", get_contract_abis)
    out = ListOutputAdder()
    lint_all([USDT], out, require_verified=require_verified)
    return out


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
    monkeypatch: pytest.MonkeyPatch, error: Exception, title: str, default_level: Output.Level
) -> None:
    out = lint_with(monkeypatch, error, require_verified=False)
    assert level_of(out, title) == default_level
    assert not out.has_errors

    out = lint_with(monkeypatch, error, require_verified=True)
    assert level_of(out, title) == Output.Level.ERROR
    assert out.has_errors


def test_transient_failure_stays_a_warning_when_verified_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    out = lint_with(monkeypatch, RATE_LIMITED, require_verified=True)
    assert level_of(out, "Could not fetch ABI") == Output.Level.WARNING
    assert not out.has_errors
