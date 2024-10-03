import re
from dataclasses import dataclass
from typing import cast

from eth_typing import ABIFunction
from eth_utils.abi import abi_to_signature, function_signature_to_4byte_selector

from erc7730.model.abi import ABI, Component, Function, InputOutput

_SOLIDITY_IDENTIFIER = r"[a-zA-Z$_][a-zA-Z$_0-9]*"
_SOLIDITY_PARAMETER_LIST = r"(" + _SOLIDITY_IDENTIFIER + r" *(" + _SOLIDITY_IDENTIFIER + r") *,? *)*"
_SOLIDITY_FUNCTION = r" *(" + _SOLIDITY_IDENTIFIER + r") *\((" + _SOLIDITY_PARAMETER_LIST + r")\)"
_SOLIDITY_FUNCTION_RE = re.compile(_SOLIDITY_FUNCTION)


def _append_path(root: str, path: str) -> str:
    return f"{root}.{path}" if root else path


def compute_paths(abi: Function) -> set[str]:
    """Compute the sets of valid paths for a Function."""

    def append_paths(path: str, params: list[InputOutput] | list[Component] | None, paths: set[str]) -> None:
        if params:
            for param in params:
                if param.components:
                    append_paths(_append_path(path, param.name), param.components, paths)  # type: ignore
                else:
                    paths.add(_append_path(path, param.name))

    paths: set[str] = set()
    append_paths("", abi.inputs, paths)
    return paths


def compute_signature(abi: Function) -> str:
    """Compute the signature of a Function."""
    abi_function = cast(ABIFunction, abi.model_dump())
    return abi_to_signature(abi_function)


def reduce_signature(signature: str) -> str | None:
    """Remove parameter names from a function signature. return None if the signature is invalid."""
    if match := _SOLIDITY_FUNCTION_RE.fullmatch(signature):
        function_name = match.group(1)
        parameters = match.group(2).split(",")
        parameters_types = [param.strip().partition(" ")[0] for param in parameters]
        return f"{function_name}({','.join(parameters_types)})"
    return None


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
