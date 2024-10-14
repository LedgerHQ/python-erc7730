import pytest

from erc7730.common import client


@pytest.mark.skip(reason="Secret management not implemented")
def test_get_contract_abis() -> None:
    result = client.get_contract_abis(chain_id=1, contract_address="0x06012c8cf97bead5deae237070f9587f8e7a266d")
    assert result is not None
    assert len(result) > 0
