import json
import os
from abc import ABC
from functools import cache
from typing import Any, TypeVar, final, override

from hishel import CacheTransport, FileStorage
from httpx import URL, BaseTransport, Client, HTTPTransport, Request, Response
from httpx._content import IteratorByteStream
from httpx_file import FileTransport
from limiter import Limiter
from pydantic import ConfigDict, TypeAdapter, ValidationError
from pydantic_string_url import FileUrl, HttpUrl
from xdg_base_dirs import xdg_cache_home

from erc7730.model.abi import ABI
from erc7730.model.base import Model
from erc7730.model.types import Address

SOURCIFY = "repo.sourcify.dev"

_T = TypeVar("_T")


class SourcifyChain(Model):
    """Sourcify supported chain info."""

    model_config = ConfigDict(strict=False, frozen=True, extra="ignore")
    chainname: str
    chainid: int
    blockexplorer: HttpUrl


@cache
def get_supported_chains() -> list[SourcifyChain]:
    """
    Get supported chains from Sourcify.

    :return: Sourcify supported chains, with name/chain id/block explorer URL
    """
    # Sourcify doesn't provide a chains API, we'll use a static list for now
    # This could be enhanced to fetch from a different source
    return []


def get_contract_abis(chain_id: int, contract_address: Address) -> list[ABI] | None:
    """
    Get contract ABIs from Sourcify.

    :param chain_id: chain id
    :param contract_address: contract address
    :return: list of ABIs or None if not found
    :raises NotImplementedError: if chain id not supported, API key not setup, or unexpected response
    """
    try:
        # Use a direct client without cache for Sourcify requests to avoid redirect issues
        direct_client = Client(timeout=30, follow_redirects=True)
        try:
            response = direct_client.get(
                f"https://{SOURCIFY}/contracts/full_match/{chain_id}/{contract_address}/metadata.json"
            )
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Sourcify returns metadata with ABI in the 'output' field
            if 'output' in data and 'abi' in data['output']:
                return TypeAdapter(list[ABI]).validate_python(data['output']['abi'])
            else:
                raise Exception("Contract source is not available on Sourcify")
        finally:
            direct_client.close()
    except Exception as e:
        if "rate limit" in str(e).lower():
            raise Exception("Sourcify rate limit exceeded, please retry") from e
        raise e


def get_contract_explorer_url(chain_id: int, contract_address: Address) -> HttpUrl:
    """
    Get contract explorer site URL (for opening in a browser).

    :param chain_id: EIP-155 chain ID
    :param contract_address: EVM contract address
    :return: URL to the contract explorer site
    :raises NotImplementedError: if chain id not supported
    """
    for chain in get_supported_chains():
        if chain.chainid == chain_id:
            return HttpUrl(f"{chain.blockexplorer}/address/{contract_address}#code")
    raise NotImplementedError(
        f"Chain ID {chain_id} is not supported, please report this to authors of python-erc7730 library"
    )


def get(model: type[_T], url: HttpUrl | FileUrl, **params: Any) -> _T:
    """
    Fetch data from a file or an HTTP URL and deserialize it.

    This method implements some automated adaptations to handle user provided URLs:
     - GitHub: adaptation to "raw.githubusercontent.com"
     - Sourcify: rate limiting, API key parameter injection

    :param url: URL to get data from
    :param model: Pydantic model to deserialize the data
    :return: deserialized response
    :raises Exception: if URL type is not supported, API key not setup, or unexpected response
    """
    with _client() as client:
        response = client.get(url, params=params).raise_for_status().content
    try:
        return TypeAdapter(model).validate_json(response)
    except ValidationError as e:
        raise Exception(f"Received unexpected response from {url}: {response.decode(errors='replace')}") from e


def _client() -> Client:
    """
    Create a new HTTP client with GitHub and Sourcify specific transports.
    :return:
    """
    cache_storage = FileStorage(base_path=xdg_cache_home() / "erc7730", ttl=7 * 24 * 3600, check_ttl_every=24 * 3600)
    http_transport = HTTPTransport()
    http_transport = GithubTransport(http_transport)
    http_transport = SourcifyTransport(http_transport)
    http_transport = CacheTransport(transport=http_transport, storage=cache_storage)
    file_transport = FileTransport()
    # TODO file storage: authorize relative paths only
    transports = {"https://": http_transport, "file://": file_transport}
    return Client(mounts=transports, timeout=10, follow_redirects=True)


class DelegateTransport(ABC, BaseTransport):
    """Base class for wrapping httpx transport."""

    def __init__(self, delegate: BaseTransport) -> None:
        self._delegate = delegate

    def handle_request(self, request: Request) -> Response:
        return self._delegate.handle_request(request)

    def close(self) -> None:
        self._delegate.close()


@final
class GithubTransport(DelegateTransport):
    """GitHub specific transport for handling raw content requests."""

    GITHUB, GITHUB_RAW = "github.com", "raw.githubusercontent.com"

    def __init__(self, delegate: BaseTransport) -> None:
        super().__init__(delegate)

    @override
    def handle_request(self, request: Request) -> Response:
        if request.url.host != self.GITHUB:
            return super().handle_request(request)

        # adapt URL
        request.url = URL(str(request.url).replace(self.GITHUB, self.GITHUB_RAW).replace("/blob/", "/"))
        request.headers.update({"Host": self.GITHUB_RAW})
        return super().handle_request(request)


@final
class SourcifyTransport(DelegateTransport):
    """Sourcify specific transport for handling rate limiting and API key parameter injection."""

    SOURCIFY_API_HOST = "SOURCIFY_API_HOST"
    SOURCIFY_API_KEY = "SOURCIFY_API_KEY"

    @Limiter(rate=10, capacity=10, consume=1)
    @override
    def handle_request(self, request: Request) -> Response:
        if request.url.host != SOURCIFY:
            return super().handle_request(request)

        # substitute base URL if provided
        if (api_host := os.environ.get(self.SOURCIFY_API_HOST)) is not None:
            request.url = request.url.copy_with(host=api_host)
            request.headers.update({"Host": api_host})

        # add API key if provided (Sourcify doesn't require API key but supports it for rate limiting)
        if (api_key := os.environ.get(self.SOURCIFY_API_KEY)) is not None:
            request.url = request.url.copy_add_param("apikey", api_key)

        # For Sourcify requests, we need to handle redirects manually to avoid cache issues
        # Create a direct client without cache for this request
        direct_client = Client(timeout=10, follow_redirects=True)
        try:
            response = direct_client.get(request.url)
            response.raise_for_status()
            return response
        finally:
            direct_client.close()
