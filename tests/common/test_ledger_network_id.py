import pytest

from erc7730.common.ledger import ledger_network_id


@pytest.mark.parametrize(
    "chain_id,network",
    [
        pytest.param(1, "ethereum", id="ethereum"),
        pytest.param(130, "unichain", id="unichain"),
        pytest.param(1301, "unichain_sepolia", id="unichain_sepolia"),
        pytest.param(137, "polygon", id="polygon"),
    ],
)
def test_known_chain_ids_map_to_their_ledger_currency_id(chain_id: int, network: str) -> None:
    """Ids are the Ledger currency ids published in @ledgerhq/cryptoassets."""
    assert ledger_network_id(chain_id) == network


def test_an_unsupported_chain_returns_none() -> None:
    """A chain Ledger has no currency for has no network id, and its deployments are skipped."""
    assert ledger_network_id(9745) is None


def test_the_mapping_is_ordered_by_chain_id() -> None:
    """The match arms are kept in ascending order, so a new chain has one obvious place to go."""
    import re
    from pathlib import Path

    source = Path(ledger_network_id.__globals__["__file__"]).read_text(encoding="utf-8")
    chain_ids = [int(m) for m in re.findall(r"case (\d+):", source)]

    assert chain_ids == sorted(chain_ids)
