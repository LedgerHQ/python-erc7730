import pytest
from pydantic import TypeAdapter
from pydantic_string_url import HttpUrl

from erc7730.common.output import RaisingOutputAdder
from erc7730.convert.resolved.constants import DefaultConstantProvider
from erc7730.model.input.context import InputContract, InputContractContext, InputDeployment
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import InputDisplay, InputFieldDescription, InputFormat
from erc7730.model.input.metadata import InputMetadata
from erc7730.model.input.path import DescriptorPathStr
from erc7730.model.paths import DescriptorPath
from erc7730.model.paths.path_parser import to_path


def _provider(**constants: str | int | bool | float | None) -> DefaultConstantProvider:
    return DefaultConstantProvider(
        InputERC7730Descriptor(
            context=InputContractContext(
                contract=InputContract(
                    abi=HttpUrl("https://example.net/abi.json"),
                    deployments=[
                        InputDeployment(chainId=1, address="0x1111111111111111111111111111111111111111"),
                        InputDeployment(chainId=42, address="0x4242424242424242424242424242424242424242"),
                    ],
                )
            ),
            metadata=InputMetadata(constants=constants),
            display=InputDisplay(
                formats={"test": InputFormat(fields=[InputFieldDescription(path=to_path("#.foo"), label="Foo")])}
            ),
        )
    )


def _descriptor_path(value: str) -> DescriptorPath:
    return TypeAdapter(DescriptorPathStr).validate_strings(value)


def test_get_string() -> None:
    assert _provider(foo="bar").get(_descriptor_path("$.metadata.constants.foo"), RaisingOutputAdder()) == "bar"


def test_get_bool() -> None:
    assert _provider(foo=False).get(_descriptor_path("$.metadata.constants.foo"), RaisingOutputAdder()) is False


def test_get_int() -> None:
    assert _provider(foo=42).get(_descriptor_path("$.metadata.constants.foo"), RaisingOutputAdder()) == 42


def test_get_float() -> None:
    assert _provider(foo=1.42).get(_descriptor_path("$.metadata.constants.foo"), RaisingOutputAdder()) == 1.42


def test_get_from_context() -> None:
    assert _provider().get(_descriptor_path("$.context.contract.abi"), RaisingOutputAdder()) == HttpUrl(
        "https://example.net/abi.json"
    )


def test_get_from_list() -> None:
    assert _provider().get(_descriptor_path("$.context.contract.deployments.[1].chainId"), RaisingOutputAdder()) == 42


def test_resolve_literal() -> None:
    assert _provider(foo="bar").resolve("baz", RaisingOutputAdder()) == "baz"


def test_resolve_constant() -> None:
    assert _provider(foo="bar").resolve(to_path("$.metadata.constants.foo"), RaisingOutputAdder()) == "bar"


def test_resolve_or_none_literal() -> None:
    assert _provider(foo="bar").resolve_or_none("baz", RaisingOutputAdder()) == "baz"


def test_resolve_or_none_constant() -> None:
    assert _provider(foo="bar").resolve_or_none(to_path("$.metadata.constants.foo"), RaisingOutputAdder()) == "bar"


def test_resolve_or_none_none() -> None:
    assert _provider(foo="bar").resolve_or_none(None, RaisingOutputAdder()) is None


def test_resolve_path_literal_data_path() -> None:
    assert _provider(foo="bar").resolve_path(to_path("#.a.b.c"), RaisingOutputAdder()) == to_path("#.a.b.c")


def test_resolve_path_literal_container_path() -> None:
    assert _provider(foo="bar").resolve_path(to_path("@.to"), RaisingOutputAdder()) == to_path("@.to")


def test_resolve_path_constant() -> None:
    assert _provider(foo="#.a.b.c").resolve_path(to_path("$.metadata.constants.foo"), RaisingOutputAdder()) == to_path(
        "#.a.b.c"
    )


def test_resolve_path_or_none_literal_data_path() -> None:
    assert _provider(foo="bar").resolve_path_or_none(to_path("#.a.b.c"), RaisingOutputAdder()) == to_path("#.a.b.c")


def test_resolve_path_or_none_literal_container_path() -> None:
    assert _provider(foo="bar").resolve_path_or_none(to_path("@.to"), RaisingOutputAdder()) == to_path("@.to")


def test_resolve_path_or_none_constant() -> None:
    assert _provider(foo="#.a.b.c").resolve_path_or_none(
        to_path("$.metadata.constants.foo"), RaisingOutputAdder()
    ) == to_path("#.a.b.c")


def test_resolve_path_or_none_none() -> None:
    assert _provider(foo="#.a.b.c").resolve_path_or_none(None, RaisingOutputAdder()) is None


@pytest.mark.raises(match='.*\\$.metadata.constants has no "baz" field.')
def test_get_invalid_no_such_constant() -> None:
    _provider(foo="bar").get(_descriptor_path("$.metadata.constants.baz"), RaisingOutputAdder())


@pytest.mark.raises(match='.*\\$.metadata.constants has no "baz" field.')
def test_get_invalid_empty_constants() -> None:
    _provider().get(_descriptor_path("$.metadata.constants.baz"), RaisingOutputAdder())


@pytest.mark.raises(match=".*Path \\$.metadata.\\[0\\] is invalid, \\$.metadata is not an array.")
def test_get_invalid_not_an_array() -> None:
    _provider(foo="bar").get(_descriptor_path("$.metadata.[0]"), RaisingOutputAdder())


@pytest.mark.raises(match=".*\\$.context.contract.deployments is an array.")
def test_get_invalid_not_a_dict() -> None:
    _provider(foo="bar").get(_descriptor_path("$.context.contract.deployments.foo"), RaisingOutputAdder())


@pytest.mark.raises(match='.*\\$.metadata.constants has no "baz" field.')
def test_resolve_invalid_no_such_constant() -> None:
    _provider(foo="bar").resolve(to_path("$.metadata.constants.baz"), RaisingOutputAdder())


@pytest.mark.raises(match='.*\\$.metadata.constants has no "baz" field.')
def test_resolve_invalid_empty_constants() -> None:
    _provider().resolve(to_path("$.metadata.constants.baz"), RaisingOutputAdder())


@pytest.mark.raises(match='.*\\$.metadata.constants has no "baz" field.')
def test_resolve_path_invalid_no_such_constant() -> None:
    _provider(foo="bar").resolve_path(to_path("$.metadata.constants.baz"), RaisingOutputAdder())


@pytest.mark.raises(match='.*\\$.metadata.constants has no "baz" field.')
def test_resolve_path_invalid_empty_constants() -> None:
    _provider().resolve_path(to_path("$.metadata.constants.baz"), RaisingOutputAdder())


@pytest.mark.raises(match='.*\\$.metadata.constants has no "baz" field.')
def test_resolve_path_or_none_invalid_no_such_constant() -> None:
    _provider(foo="bar").resolve_path_or_none(to_path("$.metadata.constants.baz"), RaisingOutputAdder())


@pytest.mark.raises(match='.*\\$.metadata.constants has no "baz" field.')
def test_resolve_path_or_none_invalid_empty_constants() -> None:
    _provider().resolve_path_or_none(to_path("$.metadata.constants.baz"), RaisingOutputAdder())
