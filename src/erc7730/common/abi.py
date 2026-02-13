from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any, cast

from eth_typing import ABIFunction
from eth_utils.abi import abi_to_signature, function_signature_to_4byte_selector
from lark import Lark, UnexpectedInput
from lark.visitors import Transformer_InPlaceRecursive

from erc7730.model.abi import ABI, Component, Function, InputOutput, StateMutability

_SIGNATURE_PARSER = parser = Lark(
    grammar=r"""
            function: identifier "(" params ")"
            
            params: (param ("," param)*)?
            ?param: named_param | named_tuple

            ?tuple: "(" params ")"
                       
            named_param: type identifier?
            named_tuple:  tuple array* identifier?

            array: "[]"
            identifier: /[a-zA-Z$_][a-zA-Z0-9$_]*/
            type: identifier array*

            %ignore " "
            """,
    start="function",
)


class FunctionTransformer(Transformer_InPlaceRecursive):
    """Visitor to transform the parsed function AST into function domain model objects."""

    def function(self, ast: Any) -> Function:
        (name, inputs) = ast
        return Function(
            name=name,
            inputs=[InputOutput(name=input.name, type=input.type, components=input.components) for input in inputs],
        )

    def params(self, ast: Any) -> list[Component]:
        return ast

    def named_param(self, ast: Any) -> Component:
        if len(ast) == 1:
            return Component(name="_", type=ast[0])
        (type_, name) = ast
        return Component(name=name, type=type_)

    def named_tuple(self, ast: Any) -> Component:
        if len(ast) == 0:
            # Should not happen, but handle gracefully
            return Component(name="_", type="tuple", components=[])

        # First element is always components
        components = ast[0]

        # Separate arrays from name
        # Arrays are "[]", name is anything else
        arrays = [elem for elem in ast[1:] if elem == "[]"]
        names = [elem for elem in ast[1:] if elem != "[]"]

        # Build type with array suffixes
        type_str = "tuple" + "".join(arrays)

        # Use name if provided, otherwise use default
        name = names[0] if names else "_"

        return Component(name=name, type=type_str, components=components)

    def array(self, ast: Any) -> str:
        return "[]"

    def identifier(self, ast: Any) -> str:
        (value,) = ast
        return value

    def type(self, ast: Any) -> str:
        if len(ast) == 0:
            # Should not happen, but handle gracefully
            return ""

        # First element is the base type identifier
        base_type = ast[0]

        # Remaining elements are array suffixes "[]"
        arrays = ast[1:]

        # Concatenate base type with all array suffixes
        return base_type + "".join(arrays)


def compute_signature(abi: Function) -> str:
    """Compute the signature of a Function."""
    abi_function = cast(ABIFunction, abi.model_dump())
    return abi_to_signature(abi_function)


def reduce_signature(signature: str) -> str:
    """Remove parameter names and spaces from a function signature."""
    return compute_signature(parse_signature(signature))


def parse_signature(signature: str) -> Function:
    """Parse a function signature."""
    try:
        return FunctionTransformer().transform(_SIGNATURE_PARSER.parse(signature))
    except UnexpectedInput as e:
        raise ValueError(f"Invalid signature: {signature}") from e


def signature_to_selector(signature: str) -> str:
    """Compute the keccak of a signature."""
    return "0x" + function_signature_to_4byte_selector(signature).hex()


def function_to_selector(abi: Function) -> str:
    """Compute the selector of a Function."""
    return signature_to_selector(compute_signature(abi))


@dataclass(kw_only=True)
class Functions:
    functions: dict[str, Function]
    proxy: bool


_READ_ONLY_MUTABILITIES = frozenset({StateMutability.pure, StateMutability.view})


def get_functions(abis: list[ABI], *, include_read_only: bool = False) -> Functions:
    """Get the functions from a list of ABIs.

    :param abis: list of ABI entries
    :param include_read_only: if False (default), filter out pure/view functions that cannot produce transactions
    :return: Functions dataclass with selector->Function mapping
    """
    functions = Functions(functions={}, proxy=False)
    for abi in abis:
        if abi.type == "function":
            if not include_read_only and abi.stateMutability in _READ_ONLY_MUTABILITIES:
                continue
            functions.functions[function_to_selector(abi)] = abi
            if abi.name in ("proxyType", "getImplementation", "implementation", "proxy__getImplementation"):
                functions.proxy = True
    return functions


class ABIDataType(StrEnum):
    """Solidity data type."""

    UINT = auto()
    INT = auto()
    UFIXED = auto()
    FIXED = auto()
    ADDRESS = auto()
    BOOL = auto()
    BYTES = auto()
    STRING = auto()
