import pytest
from typing_extensions import TypeVar

_T = TypeVar("_T")


def single_or_skip(value: _T | dict[str, _T] | None) -> _T:
    assert value is not None
    if isinstance(value, dict):
        pytest.skip("Multiple descriptors tests not supported")
    return value
