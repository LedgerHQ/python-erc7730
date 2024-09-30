import os

import requests
from pydantic import RootModel

from erc7730.model.abi import ABI


def get_contract_abis(chain_id: int, contract_address: str) -> list[ABI] | None:
    match chain_id:
        case 1:
            return get_contract_abis_1(contract_address)
        case _:
            return None


def get_contract_abis_1(contract_address: str) -> list[ABI] | None:
    if (api_key := os.environ.get("ETHERSCAN_API_KEY")) is None:
        return None
    resp = requests.get(
        f"https://api.etherscan.io/api"
        f"?module=contract"
        f"&action=getabi"
        f"&address={contract_address}"
        f"&apikey={api_key}",
        timeout=10,
    )
    resp.raise_for_status()
    model: type[RootModel[list[ABI]]] = RootModel[list[ABI]]
    json = resp.json()
    return model.model_validate_json(json["result"]).root
