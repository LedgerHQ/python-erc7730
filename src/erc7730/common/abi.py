import re
from dataclasses import dataclass
from typing import cast

from eth_typing import ABIFunction
from eth_utils.abi import abi_to_signature, function_signature_to_4byte_selector

from erc7730.model.abi import ABI, Component, Function, InputOutput

_SIGNATURE_SPACES_PRE_CLEANUP = r"(,|\()( +)"
_SIGNATURE_CLEANUP = r"( +[^,\(\)]*)(\(|,|\))"

_SIGNATURE_SPACES_PRE_CLEANUP_RE = re.compile(_SIGNATURE_SPACES_PRE_CLEANUP)
_SIGNATURE_CLEANUP_RE = re.compile(_SIGNATURE_CLEANUP)


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
    """Remove parameter names and spaces from a function signature. Behaviour is undefined on invalid signature."""
    # Note: Implementation is hackish, but as parameter types can be tuples that can be nested,
    # it would require a full parser to do it properly.
    # Test coverage should be enough to ensure it works as expected on valid signatures.
    return re.sub(_SIGNATURE_CLEANUP_RE, r"\2", re.sub(_SIGNATURE_SPACES_PRE_CLEANUP_RE, r"\1", signature))


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
