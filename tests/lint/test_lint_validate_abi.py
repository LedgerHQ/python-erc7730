import pytest

from erc7730.common import client
from erc7730.common.output import ListOutputAdder, Output
from erc7730.lint.lint_validate_abi import ValidateABILinter
from erc7730.model.resolved.context import ResolvedContractContext

CONTEXT = ResolvedContractContext.model_validate(
    {
        "contract": {
            "abi": [],
            "deployments": [{"chainId": 1, "address": "0x0000000000000000000000000000000000000001"}],
        }
    }
)

NOT_VERIFIED = client.ContractNotVerifiedError("contract 0x1 on chain 1 is not verified on Sourcify")
IMPLEMENTATION_NOT_VERIFIED = client.ProxyImplementationNotVerifiedError("contract 0x1 on chain 1 is a proxy")
CHAIN_NOT_SUPPORTED = client.ChainNotSupportedError("chain 1 is not supported by Sourcify")
RATE_LIMITED = Exception("Sourcify rate limit exceeded, please retry")


@pytest.mark.parametrize(
    ("error", "title", "default_level"),
    [
        (NOT_VERIFIED, "Contract not verified", Output.Level.WARNING),
        (IMPLEMENTATION_NOT_VERIFIED, "Proxy implementation not verified", Output.Level.WARNING),
        (CHAIN_NOT_SUPPORTED, "Chain not supported", Output.Level.INFO),
        (RATE_LIMITED, "Could not fetch ABI", Output.Level.WARNING),
    ],
)
def test_fetch_failure_is_an_error_only_when_verified_is_required(
    monkeypatch: pytest.MonkeyPatch, error: Exception, title: str, default_level: Output.Level
) -> None:
    def get_contract_abis(chain_id: int, contract_address: str) -> None:
        raise error

    monkeypatch.setattr(client, "get_contract_abis", get_contract_abis)

    for require_verified, level in ((False, default_level), (True, Output.Level.ERROR)):
        out = ListOutputAdder()
        ValidateABILinter(require_verified=require_verified)._validate_contract_abis(CONTEXT, out)
        assert [(output.title, output.level) for output in out.outputs] == [(title, level)]
