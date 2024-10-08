import contextlib
import operator
from collections.abc import Callable
from functools import reduce
from typing import Any


def get_by_path(root: dict[str, Any], *paths: str) -> Any:
    """Access a nested object in root by item sequence."""
    return reduce(operator.getitem, list(paths), root)


def is_in_path(root: dict[str, Any], *paths: str) -> bool:
    """Check if a key-value in a nested object in root by item sequence exists."""
    try:
        get_by_path(root, *paths)
        return True
    except KeyError:
        return False


def del_by_path(root: dict[str, Any], *paths: str) -> None:
    """Delete a key-value in a nested object in root by item sequence."""
    path_list = list(paths)
    with contextlib.suppress(KeyError):
        del get_by_path(root, *path_list[:-1])[path_list[-1]]


def map_by_path(root: dict[str, Any], func: Callable[[Any], Any], *paths: str) -> None:
    """Map a function to a key-value in a nested object in root by item sequence."""
    path_list = list(paths)
    with contextlib.suppress(KeyError):
        get_by_path(root, *path_list[:-1])[path_list[-1]] = func(get_by_path(root, *paths))
