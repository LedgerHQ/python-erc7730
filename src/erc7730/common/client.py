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


SCAN_SITES = {
    1: ScanSite(host="api.etherscan.io", api_key="ETHERSCAN_API_KEY"),
    56: ScanSite(host="api.bscscan.com", api_key="BSCSCAN_API_KEY"),
    137: ScanSite(host="api.polygonscan.io", api_key="POLYGONSCAN_API_KEY"),
    1101: ScanSite(host="api-zkevm.polygonscan.com", api_key="POLYGONSKEVMSCAN_API_KEY"),
    42161: ScanSite(host="api.arbiscan.io", api_key="ARBISCAN_API_KEY"),
    8453: ScanSite(host="api.basescan.io", api_key="BASESCAN_API_KEY"),
    10: ScanSite(host="api-optimistic.etherscan.io", api_key="OPTIMISMSCAN_API_KEY"),
    25: ScanSite(host="api.cronoscan.com", api_key="CRONOSCAN_API_KEY"),
    250: ScanSite(host="api.ftmscan.com", api_key="FANTOMSCAN_API_KEY"),
    284: ScanSite(host="api-moonbeam.moonscan.io", api_key="MOONSCAN_API_KEY"),
    199: ScanSite(host="api.bttcscan.com", api_key="BTTCSCAN_API_KEY"),
    59144: ScanSite(host="api.lineascan.build", api_key="LINEASCAN_API_KEY"),
    534352: ScanSite(host="api.scrollscan.com", api_key="SCROLLSCAN_API_KEY"),
    421614: ScanSite(host="api-sepolia.arbiscan.io", api_key="ARBISCAN_SEPOLIA_API_KEY"),
    84532: ScanSite(host="api-sepolia.basescan.org", api_key="BASESCAN_SEPOLIA_API_KEY"),
    11155111: ScanSite(host="api-sepolia.etherscan.io", api_key="ETHERSCAN_SEPOLIA_API_KEY"),
    11155420: ScanSite(host="api-sepolia-optimistic.etherscan.io", api_key="OPTIMISMSCAN_SEPOLIA_API_KEY"),
    534351: ScanSite(host="api-sepolia.scrollscan.com", api_key="SCROLLSCAN_SEPOLIA_API_KEY"),
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
