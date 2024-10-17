import os
from dataclasses import dataclass
from io import UnsupportedOperation
from typing import Any

import requests
from pydantic import RootModel
from pydantic_string_url import FileUrl, HttpUrl

from erc7730.common.pydantic import _BaseModel
from erc7730.model.abi import ABI


@dataclass
class ScanSite:
    host: str
    api_key: str
    url: str


SCAN_SITES = {
    1: ScanSite(host="api.etherscan.io", api_key="ETHERSCAN_API_KEY", url="https://etherscan.io"),
    56: ScanSite(host="api.bscscan.com", api_key="BSCSCAN_API_KEY", url="https://bscscan.com"),
    137: ScanSite(host="api.polygonscan.com", api_key="POLYGONSCAN_API_KEY", url="https://polygonscan.com"),
    1101: ScanSite(
        host="api-zkevm.polygonscan.com",
        api_key="POLYGONSKEVMSCAN_API_KEY",
        url="https://zkevm.polygonscan.com",
    ),
    42161: ScanSite(host="api.arbiscan.io", api_key="ARBISCAN_API_KEY", url="https://arbiscan.io"),
    8453: ScanSite(host="api.basescan.io", api_key="BASESCAN_API_KEY", url="https://basescan.io"),
    10: ScanSite(
        host="api-optimistic.etherscan.io",
        api_key="OPTIMISMSCAN_API_KEY",
        url="https://optimistic.etherscan.io",
    ),
    25: ScanSite(host="api.cronoscan.com", api_key="CRONOSCAN_API_KEY", url="https://cronoscan.com"),
    250: ScanSite(host="api.ftmscan.com", api_key="FANTOMSCAN_API_KEY", url="https://ftmscan.com"),
    284: ScanSite(host="api-moonbeam.moonscan.io", api_key="MOONSCAN_API_KEY", url="https://moonbeam.moonscan.io"),
    199: ScanSite(host="api.bttcscan.com", api_key="BTTCSCAN_API_KEY", url="https://bttcscan.com"),
    59144: ScanSite(host="api.lineascan.build", api_key="LINEASCAN_API_KEY", url="https://lineascan.build"),
    534352: ScanSite(host="api.scrollscan.com", api_key="SCROLLSCAN_API_KEY", url="https://scrollscan.com"),
    421614: ScanSite(
        host="api-sepolia.arbiscan.io", api_key="ARBISCAN_SEPOLIA_API_KEY", url="https://sepolia.arbiscan.io"
    ),
    84532: ScanSite(
        host="api-sepolia.basescan.org",
        api_key="BASESCAN_SEPOLIA_API_KEY",
        url="https://sepolia.basescan.org",
    ),
    11155111: ScanSite(
        host="api-sepolia.etherscan.io",
        api_key="ETHERSCAN_SEPOLIA_API_KEY",
        url="https://sepolia.etherscan.io",
    ),
    11155420: ScanSite(
        host="api-sepolia-optimistic.etherscan.io",
        api_key="OPTIMISMSCAN_SEPOLIA_API_KEY",
        url="https://sepolia.optimistic.etherscan.io",
    ),
    534351: ScanSite(
        host="api-sepolia.scrollscan.com",
        api_key="SCROLLSCAN_SEPOLIA_API_KEY",
        url="https://sepolia.scrollscan.com",
    ),
}


def get_contract_abis(chain_id: int, contract_address: str) -> list[ABI] | None:
    """
    Get contract ABIs from an etherscan-like site.

    :param chain_id: EIP-155 chain ID
    :param contract_address: EVM contract address
    :return: deserialized list of ABIs
    :raises ValueError: if chain id not supported, API key not setup, or unexpected response
    """
    if (site := SCAN_SITES.get(chain_id)) is None:
        raise UnsupportedOperation(
            f"Chain ID {chain_id} is not supported, please report this to authors of " f"python-erc7730 library"
        )
    return get(
        url=HttpUrl(f"https://{site.host}/api?module=contract&action=getabi&address={contract_address}"),
        model=RootModel[list[ABI]],
    ).root


def get_contract_url(chain_id: int, contract_address: str) -> str:
    if (site := SCAN_SITES.get(chain_id)) is None:
        raise UnsupportedOperation(
            f"Chain ID {chain_id} is not supported, please report this to authors of " f"python-erc7730 library"
        )
    return f"{site.url}/address/{contract_address}#code"


def get(url: FileUrl | HttpUrl, model: type[_BaseModel]) -> _BaseModel:
    """
    Fetch data from a file or an HTTP URL and deserialize it.

    This method implements some automated adaptations to handle user provided URLs:
     - adaptation to "raw.githubusercontent.com" for GitHub URLs
     - injection of API key parameters for etherscan-like sites
     - unwrapping of "result" field for etherscan-like sites

    :param url: URL to get data from
    :param model: Pydantic model to deserialize the data
    :return: deserialized response
    :raises ValueError: if URL type is not supported, API key not setup, or unexpected response
    """
    # TODO add disk cache support
    if isinstance(url, HttpUrl):
        response = requests.get(_adapt_http_url(url), timeout=10)
        response.raise_for_status()
        data = _adapt_http_response(url, response.json())
        if isinstance(data, str):
            return model.model_validate_json(data)
        return model.model_validate(data)
    if isinstance(url, FileUrl):
        # TODO add support for file:// URLs
        raise NotImplementedError("file:// URL support is not implemented")
    raise ValueError(f"Unsupported URL type: {type(url)}")


def _adapt_http_url(url: HttpUrl) -> HttpUrl:
    if url.startswith("https://github.com"):
        return HttpUrl(url.replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/"))

    for scan_site in SCAN_SITES.values():
        if url.startswith(f"https://{scan_site.host}"):
            if (api_key := os.environ.get(scan_site.api_key)) is None:
                raise ValueError(f"{scan_site.api_key} environment variable is required")
            return HttpUrl(f"{url}&apikey={api_key}")

    return url


def _adapt_http_response(url: HttpUrl, response: Any) -> Any:
    for scan_site in SCAN_SITES.values():
        if url.startswith(f"https://{scan_site.host}") and (result := response.get("result")) is not None:
            return result
    return response
