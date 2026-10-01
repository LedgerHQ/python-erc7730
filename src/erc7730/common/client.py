import json
import os
from abc import ABC
from functools import cache
from typing import Any, TypeVar, final, override

from hishel import CacheTransport, FileStorage
from httpx import URL, BaseTransport, Client, HTTPStatusError, HTTPTransport, Request, Response, codes
from httpx._content import IteratorByteStream
from httpx_file import FileTransport
from httpx_retries import RetryTransport
from limiter import Limiter
from pydantic import ConfigDict, Field, TypeAdapter, ValidationError
from pydantic_string_url import FileUrl, HttpUrl
from xdg_base_dirs import xdg_cache_home

from erc7730.model.abi import ABI
from erc7730.model.base import Model
from erc7730.model.types import Address

# ruff: noqa: UP047
# ruff: noqa: N815 - camel case field names are tolerated to match schema

ETHERSCAN = "api.etherscan.io"
SOURCIFY = "sourcify.dev"

ERC7730_NO_CACHE = "ERC7730_NO_CACHE"
CACHE_TTL = 3600

_T = TypeVar("_T")


class SourcifyChain(Model):
    """Sourcify chain info, restricted to the fields used by this library."""

    model_config = ConfigDict(strict=False, frozen=True, extra="ignore")
    name: str
    chainId: int
    supported: bool = False


class SourcifyImplementation(Model):
    """Sourcify proxy implementation, restricted to the fields used by this library."""

    model_config = ConfigDict(strict=False, frozen=True, extra="ignore")
    address: Address


class SourcifyError(Model):
    """Sourcify error, restricted to the fields used by this library."""

    model_config = ConfigDict(strict=False, frozen=True, extra="ignore")
    customCode: str
    message: str


class SourcifyProxyResolution(Model):
    """Sourcify proxy resolution, restricted to the fields used by this library."""

    model_config = ConfigDict(strict=False, frozen=True, extra="ignore")
    isProxy: bool = False
    implementations: list[SourcifyImplementation] = Field(default_factory=list)
    proxyResolutionError: SourcifyError | None = None


class SourcifyContract(Model):
    """Sourcify verified contract, restricted to the fields used by this library."""

    model_config = ConfigDict(strict=False, frozen=True, extra="ignore")
    abi: list[ABI]
    proxyResolution: SourcifyProxyResolution | None = None


class ContractNotVerifiedError(Exception):
    """Contract is not verified on Sourcify."""


class ProxyImplementationNotVerifiedError(ContractNotVerifiedError):
    """Contract is a proxy, and one of its implementations is not verified on Sourcify."""


class ChainNotSupportedError(Exception):
    """Chain is not supported by Sourcify."""


@cache
def get_supported_chains() -> list[SourcifyChain]:
    """
    Get supported chains from Sourcify.

    :return: Sourcify supported chains, with name/chain id
    """
    chains = get(url=HttpUrl(f"https://{SOURCIFY}/server/chains"), model=list[SourcifyChain], force_cache=True)
    return [chain for chain in chains if chain.supported]


@cache
def get_contract_abis(chain_id: int, contract_address: Address) -> list[ABI]:
    """
    Get contract ABIs from Sourcify.

    :param chain_id: EIP-155 chain ID
    :param contract_address: EVM contract address
    :return: deserialized list of ABIs
    :raises ContractNotVerifiedError: if contract, or one of its proxy implementations, is not verified on Sourcify
    :raises ChainNotSupportedError: if chain is not supported by Sourcify
    :raises Exception: if unexpected response
    """
    return get_contract_abis_from_sourcify(chain_id, contract_address)


def get_contract_abis_from_sourcify(chain_id: int, contract_address: Address) -> list[ABI]:
    """
    Get contract ABIs from Sourcify.

    If Sourcify resolves the contract as a proxy, the ABIs of its implementations are appended to the ABIs of the
    proxy, following nested proxies.

    :param chain_id: EIP-155 chain ID
    :param contract_address: EVM contract address
    :return: deserialized list of ABIs
    :raises ContractNotVerifiedError: if contract is not verified on Sourcify
    :raises ProxyImplementationNotVerifiedError: if contract is a proxy and an implementation is not verified
    :raises ChainNotSupportedError: if chain is not supported by Sourcify
    :raises Exception: if unexpected response
    """
    contract = _get_sourcify_contract(chain_id, contract_address)
    abis = list(contract.abi)
    visited = {contract_address.lower()}
    pending = _get_implementation_addresses(contract)
    while pending:
        if (address := pending.pop(0)).lower() in visited:
            continue
        visited.add(address.lower())
        try:
            implementation = _get_sourcify_contract(chain_id, address)
        except ContractNotVerifiedError as e:
            raise ProxyImplementationNotVerifiedError(
                f"contract {contract_address} on chain {chain_id} is a proxy, and its implementation {address} is not "
                f"verified on Sourcify"
            ) from e
        abis.extend(implementation.abi)
        pending.extend(_get_implementation_addresses(implementation))
    return abis


def _get_implementation_addresses(contract: SourcifyContract) -> list[Address]:
    if (resolution := contract.proxyResolution) is None or not resolution.isProxy:
        return []
    return [implementation.address for implementation in resolution.implementations]


def _get_sourcify_contract(chain_id: int, contract_address: Address) -> SourcifyContract:
    try:
        contract = get(
            url=HttpUrl(f"https://{SOURCIFY}/server/v2/contract/{chain_id}/{contract_address}"),
            fields="abi,proxyResolution",
            model=SourcifyContract,
            force_cache=True,
        )
    except HTTPStatusError as e:
        if e.response.status_code == codes.NOT_FOUND:
            raise ContractNotVerifiedError(
                f"contract {contract_address} on chain {chain_id} is not verified on Sourcify"
            ) from e
        if e.response.status_code == codes.BAD_REQUEST:
            error = _parse_sourcify_error(e.response)
            if error is not None and error.customCode == "unsupported_chain":
                raise ChainNotSupportedError(f"chain {chain_id} is not supported by Sourcify") from e
            raise Exception(f"Sourcify rejected the request: {error.message if error else e}") from e
        if e.response.status_code == codes.TOO_MANY_REQUESTS:
            raise Exception("Sourcify rate limit exceeded, please retry") from e
        raise e
    # proxy resolution is computed at request time, a failure must not be mistaken for a regular contract
    if (resolution := contract.proxyResolution) is not None and (error := resolution.proxyResolutionError) is not None:
        raise Exception(f"Sourcify could not resolve whether {contract_address} is a proxy: {error.message}")
    return contract


def _parse_sourcify_error(response: Response) -> SourcifyError | None:
    try:
        return SourcifyError.model_validate_json(response.read())
    except ValidationError:
        return None


def get_contract_explorer_url(chain_id: int, contract_address: Address) -> HttpUrl:
    """
    Get contract explorer site URL (for opening in a browser).

    :param chain_id: EIP-155 chain ID
    :param contract_address: EVM contract address
    :return: URL to the contract on the Sourcify repository
    """
    return HttpUrl(f"https://repo.{SOURCIFY}/{chain_id}/{contract_address}")


def get(model: type[_T], url: HttpUrl | FileUrl, *, force_cache: bool = False, **params: Any) -> _T:
    """
    Fetch data from a file or an HTTP URL and deserialize it.

    This method implements some automated adaptations to handle user provided URLs:
     - GitHub: adaptation to "raw.githubusercontent.com"
     - Etherscan: rate limiting, API key parameter injection, "result" field unwrapping

    Responses are cached on disk according to their caching headers, unless the ERC7730_NO_CACHE environment variable
    is set.

    :param url: URL to get data from
    :param model: Pydantic model to deserialize the data
    :param force_cache: cache the response even if it has no caching headers (for CACHE_TTL seconds)
    :param params: query parameters
    :return: deserialized response
    :raises Exception: if URL type is not supported, API key not setup, or unexpected response
    """
    with _client() as client:
        response = client.get(url, params=params, extensions={"force_cache": force_cache}).raise_for_status().content
    try:
        return TypeAdapter(model).validate_json(response)
    except ValidationError as e:
        raise Exception(f"Received unexpected response from {url}: {response.decode(errors='replace')}") from e


def _client() -> Client:
    """
    Create a new HTTP client with GitHub and Etherscan specific transports.
    :return:
    """
    http_transport: BaseTransport = HTTPTransport()
    http_transport = GithubTransport(http_transport)
    http_transport = EtherscanTransport(http_transport)
    http_transport = SourcifyTransport(http_transport)
    http_transport = RetryTransport(transport=http_transport)
    if os.environ.get(ERC7730_NO_CACHE) is None:
        cache_storage = FileStorage(base_path=xdg_cache_home() / "erc7730", ttl=CACHE_TTL, check_ttl_every=CACHE_TTL)
        http_transport = CacheTransport(transport=http_transport, storage=cache_storage)
    file_transport = FileTransport()
    # TODO file storage: authorize relative paths only
    transports = {"https://": http_transport, "file://": file_transport}
    return Client(mounts=transports, timeout=10)


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
    """Sourcify specific transport for handling token header injection."""

    SOURCIFY_TOKEN = "SOURCIFY_TOKEN"  # nosec B105 - environment variable name, not a secret

    @override
    def handle_request(self, request: Request) -> Response:
        if request.url.host != SOURCIFY:
            return super().handle_request(request)

        # add token if provided, it exempts the caller from rate limiting
        if (token := os.environ.get(self.SOURCIFY_TOKEN)) is not None:
            request.headers.update({"X-Sourcify-Token": token})
        return super().handle_request(request)


@final
class EtherscanTransport(DelegateTransport):
    """Etherscan specific transport for handling rate limiting, API key parameter injection, response unwrapping."""

    ETHERSCAN_API_HOST = "ETHERSCAN_API_HOST"
    ETHERSCAN_API_KEY = "ETHERSCAN_API_KEY"

    @Limiter(rate=5, capacity=5, consume=1)
    @override
    def handle_request(self, request: Request) -> Response:
        if request.url.host != ETHERSCAN:
            return super().handle_request(request)

        # substitute base URL if provided
        if (api_host := os.environ.get(self.ETHERSCAN_API_HOST)) is not None:
            request.url = request.url.copy_with(host=api_host)
            request.headers.update({"Host": api_host})

        # add API key if provided
        if (api_key := os.environ.get(self.ETHERSCAN_API_KEY)) is not None or (
            api_key := os.environ.get(f"SCAN_{self.ETHERSCAN_API_KEY}")
        ) is not None:
            request.url = request.url.copy_add_param("apikey", api_key)

        # read response
        response = super().handle_request(request)
        response.read()
        response.close()

        # unwrap result, sometimes containing JSON directly, sometimes JSON in a string
        try:
            if (result := response.json().get("result")) is not None:
                data = result if isinstance(result, str) else json.dumps(result)
                # Implement correct status code as Etherscan API returns 200 even in this case
                if "Max calls per sec rate limit reached" in data:
                    return Response(status_code=429, stream=IteratorByteStream([data.encode()]))
                return Response(status_code=response.status_code, stream=IteratorByteStream([data.encode()]))
        except Exception:
            pass  # nosec B110 - intentional try/except/pass

        raise Exception(f"Unexpected response from Etherscan: {response.content.decode(errors='replace')}")
