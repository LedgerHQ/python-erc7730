from pydantic_string_url import HttpUrl

from erc7730.common import client
from erc7730.model.abi import ABI


def test_get_supported_chains() -> None:
    result = client.get_supported_chains()
    assert result is not None
    assert len(result) >= 50
    names = {chain.chainname for chain in result}
    assert "Ethereum Mainnet" in names
    assert "Sepolia Testnet" in names
    assert "Holesky Testnet" in names
    assert "BNB Smart Chain Mainnet" in names
    assert "BNB Smart Chain Testnet" in names
    assert "Polygon Mainnet" in names
    assert "Polygon Amoy Testnet" in names
    assert "Polygon zkEVM Mainnet" in names
    assert "Polygon zkEVM Cardona Testnet" in names
    assert "Base Mainnet" in names
    assert "Base Sepolia Testnet" in names
    assert "Arbitrum One Mainnet" in names
    assert "Arbitrum Nova Mainnet" in names
    assert "Arbitrum Sepolia Testnet" in names
    assert "Linea Mainnet" in names
    assert "Linea Sepolia Testnet" in names
    assert "Fantom Opera Mainnet" in names
    assert "Fantom Testnet" in names
    assert "Blast Mainnet" in names
    assert "Blast Sepolia Testnet" in names
    assert "OP Mainnet" in names
    assert "OP Sepolia Testnet" in names
    assert "Avalanche C-Chain" in names
    assert "Avalanche Fuji Testnet" in names
    assert "BitTorrent Chain Mainnet" in names
    assert "BitTorrent Chain Testnet" in names
    assert "Celo Mainnet" in names
    assert "Celo Alfajores Testnet" in names
    assert "Cronos Mainnet" in names
    assert "Fraxtal Mainnet" in names
    assert "Fraxtal Testnet" in names
    assert "Gnosis" in names
    assert "Kroma Mainnet" in names
    assert "Kroma Sepolia Testnet" in names
    assert "Mantle Mainnet" in names
    assert "Mantle Sepolia Testnet" in names
    assert "Moonbeam Mainnet" in names
    assert "Moonriver Mainnet" in names
    assert "Moonbase Alpha Testnet" in names
    assert "opBNB Mainnet" in names
    assert "opBNB Testnet" in names
    assert "Scroll Mainnet" in names
    assert "Scroll Sepolia Testnet" in names
    assert "Taiko Mainnet" in names
    assert "Taiko Hekla L2 Testnet" in names
    assert "WEMIX3.0 Mainnet" in names
    assert "WEMIX3.0 Testnet" in names
    assert "zkSync Mainnet" in names
    assert "zkSync Sepolia Testnet" in names
    assert "Xai Mainnet" in names
    assert "Xai Sepolia Testnet" in names


def test_get_contract_abis() -> None:
    result = client.get_contract_abis(chain_id=1, contract_address="0x06012c8cf97bead5deae237070f9587f8e7a266d")
    assert result is not None
    assert len(result) > 0


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
