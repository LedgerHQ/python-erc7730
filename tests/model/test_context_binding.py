from typing import Any

import pytest
from pydantic import ValidationError

from erc7730.model.input.context import InputContract as InputContractV1
from erc7730.model.input.context import InputEIP712 as InputEIP712V1
from erc7730.model.input.v2.context import InputContract as InputContractV2
from erc7730.model.input.v2.context import InputEIP712 as InputEIP712V2
from erc7730.model.resolved.context import ResolvedEIP712 as ResolvedEIP712V1
from erc7730.model.resolved.v2.context import ResolvedEIP712 as ResolvedEIP712V2

# Live domain separator of Polygon PoS USDT, whose domain carries the chain id in
# `salt` and therefore has no `chainId` member to bind a deployment against.
DOMAIN_SEPARATOR = "0x7b43b7deae87806d0ace67d6c8e9e347fc85db8ad198e756e5c17d126fef9a05"
DEPLOYMENTS = [{"chainId": 137, "address": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"}]

EIP712_MODELS = [
    pytest.param(InputEIP712V1, {"schemas": []}, id="input_v1"),
    pytest.param(InputEIP712V2, {}, id="input_v2"),
    pytest.param(ResolvedEIP712V1, {"schemas": []}, id="resolved_v1"),
    pytest.param(ResolvedEIP712V2, {}, id="resolved_v2"),
]


@pytest.mark.parametrize("model,extra", EIP712_MODELS)
def test_eip712_binds_through_domain_separator_alone(model: Any, extra: dict[str, Any]) -> None:
    """A salt domain has no chainId, so it can only bind through domainSeparator."""
    context = model(domainSeparator=DOMAIN_SEPARATOR, **extra)

    assert context.deployments == []
    assert context.domainSeparator == DOMAIN_SEPARATOR


@pytest.mark.parametrize("model,extra", EIP712_MODELS)
def test_eip712_binds_through_deployments_alone(model: Any, extra: dict[str, Any]) -> None:
    """The existing form, binding by deployment, keeps working."""
    context = model(deployments=DEPLOYMENTS, **extra)

    assert len(context.deployments) == 1
    assert context.domainSeparator is None


@pytest.mark.parametrize("model,extra", EIP712_MODELS)
def test_eip712_binds_through_both(model: Any, extra: dict[str, Any]) -> None:
    """Both constraints together are allowed."""
    context = model(deployments=DEPLOYMENTS, domainSeparator=DOMAIN_SEPARATOR, **extra)

    assert len(context.deployments) == 1
    assert context.domainSeparator == DOMAIN_SEPARATOR


@pytest.mark.parametrize("model,extra", EIP712_MODELS)
def test_eip712_requires_one_binding(model: Any, extra: dict[str, Any]) -> None:
    """An unbound EIP-712 context is still rejected."""
    with pytest.raises(ValidationError) as error:
        model(**extra)

    assert "at least one of deployments or domainSeparator" in str(error.value)


@pytest.mark.parametrize(
    "model,extra",
    [
        pytest.param(InputContractV1, {"abi": []}, id="input_v1"),
        pytest.param(InputContractV2, {"abi": []}, id="input_v2"),
    ],
)
def test_contract_still_requires_deployments(model: Any, extra: dict[str, Any]) -> None:
    """Only the EIP-712 context is relaxed; a contract must still declare where it lives."""
    with pytest.raises(ValidationError):
        model(**extra)
