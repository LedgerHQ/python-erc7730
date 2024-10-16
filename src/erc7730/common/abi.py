from dataclasses import dataclass
from typing import Any, cast

from eth_typing import ABIFunction
from eth_utils.abi import abi_to_signature, function_signature_to_4byte_selector
from lark import Lark, UnexpectedInput
from lark.visitors import Transformer_InPlaceRecursive

from erc7730.model.abi import ABI, Component, Function, InputOutput

_SIGNATURE_PARSER = parser = Lark(
    grammar=r"""
            function: identifier "(" top_level_params ")"
            
            top_level_params: (top_level_param ("," top_level_param)*)?
            ?top_level_param: named_top_level_param | named_top_level_tuple
            
            inner_params: (inner_param ("," inner_param)*)?
            ?inner_param: named_inner_param | named_inner_tuple

            ?tuple: "(" inner_params ")"
            
            named_inner_param: type identifier?
            named_inner_tuple:  tuple identifier?
            
            named_top_level_param: type identifier?
            named_top_level_tuple:  tuple identifier?

            array: "[]"
            identifier: /[a-zA-Z$_][a-zA-Z0-9$_]*/
            type: identifier array?

            %ignore " "
            """,
    start="function",
)


class FunctionTransformer(Transformer_InPlaceRecursive):
    """Visitor to transform the parsed function AST into function domain model objects."""

    def function(self, ast: Any) -> Function:
        (name, inputs) = ast
        return Function(name=name, inputs=inputs)

    def top_level_params(self, ast: Any) -> list[InputOutput]:
        return ast

    def inner_params(self, ast: Any) -> list[Component]:
        return ast

    def named_top_level_param(self, ast: Any) -> InputOutput:
        if len(ast) == 1:
            return InputOutput(name="_", type=ast[0])
        (type_, name) = ast
        return InputOutput(name=name, type=type_)

    def named_top_level_tuple(self, ast: Any) -> InputOutput:
        if len(ast) == 1:
            return InputOutput(name="_", type="tuple", components=ast[0])
        (components, name) = ast
        return InputOutput(name=name, type="tuple", components=components)

    def named_inner_param(self, ast: Any) -> Component:
        if len(ast) == 1:
            return Component(name="_", type=ast[0])
        (type_, name) = ast
        return Component(name=name, type=type_)

    def named_inner_tuple(self, ast: Any) -> Component:
        if len(ast) == 1:
            return Component(name="_", type="tuple", components=ast[0])
        (components, name) = ast
        return Component(name=name, type="tuple", components=components)

    def array(self, ast: Any) -> str:
        return "[]"

    def identifier(self, ast: Any) -> str:
        (value,) = ast
        return value

    def type(self, ast: Any) -> str:
        if len(ast) == 1:
            return ast[0]

        (value, array) = ast
        return value + array


def _append_path(root: str, path: str) -> str:
    return f"{root}.{path}" if root else path


def compute_paths(abi: Function) -> set[str]:
    """Compute the sets of valid paths for a Function."""

    def append_paths(path: str, params: list[InputOutput] | list[Component] | None, paths: set[str]) -> None:
        if params:
            for param in params:
                name = param.name + ".[]" if param.type.endswith("[]") else param.name
                if param.components:
                    append_paths(_append_path(path, name), param.components, paths)  # type: ignore
                else:
                    paths.add(_append_path(path, name))

    paths: set[str] = set()
    append_paths("", abi.inputs, paths)
    return paths


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


def get_functions(abis: list[ABI]) -> Functions:
    """Get the functions from a list of ABIs."""
    functions = Functions(functions={}, proxy=False)
    for abi in abis:
        if abi.type == "function":
            functions.functions[function_to_selector(abi)] = abi
            if abi.name in ("proxyType", "getImplementation", "implementation"):
                functions.proxy = True
    return functions
