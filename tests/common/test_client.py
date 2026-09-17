import pytest
from pydantic_string_url import HttpUrl

from erc7730.common import client
from erc7730.model.abi import ABI


def test_get_supported_chains() -> None:
    result = client.get_supported_chains()
    assert result is not None
    assert len(result) >= 50
    names = {chain.name for chain in result}
    assert "Ethereum Mainnet" in names
    assert "Ethereum Sepolia Testnet" in names
    assert "BNB Smart Chain Mainnet" in names
    assert "BNB Smart Chain Testnet" in names
    assert "Polygon Mainnet" in names
    assert "Polygon Amoy Testnet" in names
    assert "Base Mainnet" in names
    assert "Base Sepolia Testnet" in names
    assert "Arbitrum One Mainnet" in names
    assert "Arbitrum Sepolia Testnet" in names
    assert "Linea Mainnet" in names
    assert "Linea Sepolia Testnet" in names
    assert "Blast Mainnet" in names
    assert "Blast Sepolia Testnet" in names
    assert "OP Mainnet" in names
    assert "OP Sepolia Testnet" in names
    assert "Avalanche C-Chain" in names
    assert "Avalanche Fuji Testnet" in names
    assert "BitTorrent Chain Mainnet" in names
    assert "BitTorrent Chain Testnet" in names
    assert "Celo Mainnet" in names
    assert "Fraxtal Mainnet" in names
    assert "Fraxtal Hoodi Testnet" in names
    assert "Gnosis" in names
    assert "Mantle Mainnet" in names
    assert "Mantle Sepolia Testnet" in names
    assert "opBNB Mainnet" in names
    assert "opBNB Testnet" in names
    assert "Taiko Mainnet" in names


def test_get_contract_explorer_url() -> None:
    result = client.get_contract_explorer_url(chain_id=1, contract_address="0x06012c8cf97bead5deae237070f9587f8e7a266d")
    assert result == "https://repo.sourcify.dev/1/0x06012c8cf97bead5deae237070f9587f8e7a266d"


def test_get_contract_abis() -> None:
    result = client.get_contract_abis(chain_id=1, contract_address="0x06012c8cf97bead5deae237070f9587f8e7a266d")
    assert result is not None
    assert len(result) > 0


def test_get_contract_abis_from_sourcify() -> None:
    result = client.get_contract_abis_from_sourcify(
        chain_id=1, contract_address="0x06012c8cf97bead5deae237070f9587f8e7a266d"
    )
    assert result is not None
    assert len(result) > 0


def test_get_contract_abis_from_sourcify_unverified_contract() -> None:
    result = client.get_contract_abis_from_sourcify(
        chain_id=1, contract_address="0x0000000000000000000000000000000000000001"
    )
    assert result is None


def test_get_contract_abis_from_sourcify_unsupported_chain() -> None:
    result = client.get_contract_abis_from_sourcify(
        chain_id=99999999, contract_address="0x06012c8cf97bead5deae237070f9587f8e7a266d"
    )
    assert result is None


def test_get_contract_abis_from_sourcify_proxy() -> None:
    # USDC is a proxy, transfer() is only defined in the ABI of its implementation
    result = client.get_contract_abis_from_sourcify(
        chain_id=1, contract_address="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    )
    assert result is not None
    names = {abi.name for abi in result if abi.type == "function"}
    assert "upgradeTo" in names
    assert "transfer" in names


def test_get_contract_abis_unverified_proxy_implementation(monkeypatch: pytest.MonkeyPatch) -> None:
    proxy = client.SourcifyContract.model_validate(
        {
            "abi": [],
            "proxyResolution": {
                "isProxy": True,
                "implementations": [{"address": "0x0000000000000000000000000000000000000001"}],
            },
        }
    )
    real_get = client.get
    client.get_contract_abis.cache_clear()
    monkeypatch.setattr(
        client, "get", lambda model, url, **params: proxy if url.endswith("eb48") else real_get(model, url, **params)
    )
    with pytest.raises(Exception, match="0x0000000000000000000000000000000000000001"):
        client.get_contract_abis(chain_id=1, contract_address="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")


def test_get_from_github() -> None:
    result1 = client.get(
        url=HttpUrl(
            "https://github.com/LedgerHQ/ledger-asset-dapps/blob/main"
            "/ethereum/uniswap/abis/0x000000000022d473030f116ddee9f6b43ac78ba3.abi.json"
        ),
        model=list[ABI],
    )
    result2 = client.get(
        url=HttpUrl(
            "https://raw.githubusercontent.com/LedgerHQ/ledger-asset-dapps/refs/heads/main"
            "/ethereum/uniswap/abis/0x000000000022d473030f116ddee9f6b43ac78ba3.abi.json"
        ),
        model=list[ABI],
    )
    assert result1 is not None
    assert result2 is not None
    assert len(result1) > 0
    assert len(result2) > 0
    assert result1 == result2
