from typing import Any

from pydantic import TypeAdapter, ValidationError

from erc7730.common.output import OutputAdder
from erc7730.model.types import Address, MixedCaseAddress

_ADDRESS = TypeAdapter(MixedCaseAddress)


def resolved_address(value: Any, out: OutputAdder) -> Address | None:
    """
    Validate a value that a parameter resolved to as an address.

    An address written in the parameter itself is validated by the input model. A value that comes from a constant
    (`$.metadata.constants...`) is not, so it is validated here with the same rules: the shape, and the EIP-55
    checksum if the address is mixed-case.

    :param value: resolved value
    :param out: error handler
    :return: the address, or None if an error was reported
    """
    try:
        return Address(_ADDRESS.validate_python(value))
    except ValidationError as e:
        return out.error(title="Invalid address", message=e.errors()[0]["msg"])
