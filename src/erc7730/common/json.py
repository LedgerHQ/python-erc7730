import json
from pathlib import Path
from typing import Any


def read_jsons_with_includes(paths: list[Path]) -> Any:
    """
    Read a list JSON files, recursively inlining any included files.

    Keys from the calling file override those of the included file (the included file defines defaults).
    Keys from the later files in the list override those of the first files.

    Note:
      - circular includes are not detected and will result in a stack overflow.
      - "includes" key can only be used at root level of an object.
    """
    result: dict[str, Any] = {}
    for path in paths:
        # noinspection PyTypeChecker
        result = _merge_dicts(result, read_json_with_includes(path))
    return result


def read_json_with_includes(path: Path) -> Any:
    """
    Read a JSON file, recursively inlining any included files.

    Keys from the calling file override those of the included file (the included file defines defaults).

    If include is a list, files are included in other they are defined, with later files overriding previous files.

    Note:
      - circular includes are not detected and will result in a stack overflow.
      - "includes" key can only be used at root level of an object.
    """
    result: Any
    with open(path) as f:
        result = json.load(f)
    if isinstance(result, dict) and (includes := result.pop("includes", None)) is not None:
        if isinstance(includes, list):
            parent = read_jsons_with_includes(paths=[path.parent / p for p in includes])
        else:
            # noinspection PyTypeChecker
            parent = read_json_with_includes(path.parent / includes)
        result = _merge_dicts(parent, result)
    return result


def _merge_dicts(d1: dict[str, Any], d2: dict[str, Any]) -> dict[str, Any]:
    """
    Merge d1 and d2, with priority to d2.

    Recursively called when dicts are encountered.

    This function assumes that if the same field is in both dicts, then the types must be the same.
    """
    merged = {}
    for key, val1 in d1.items():
        if (val2 := d2.get(key)) is not None:
            if isinstance(val1, dict):
                merged[key] = _merge_dicts(d1=val1, d2=val2)
            else:
                merged[key] = val2
        else:
            merged[key] = val1
    return {**d2, **merged}
