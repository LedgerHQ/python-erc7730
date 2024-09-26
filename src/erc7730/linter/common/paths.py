from dataclasses import dataclass
from erc7730.model.context import EIP712JsonSchema, NameType
from erc7730.model.display import Field, Format, Reference, FieldDescription, NestedFields, TokenAmountParameters

ARRAY_SUFFIX = "[]"


def _append_path(root: str, path: str) -> str:
    return f"{root}.{path}" if root else path


def _remove_slicing(token_path: str) -> str:
    return token_path.split("[")[0]


def compute_eip712_paths(schema: EIP712JsonSchema) -> set[str]:
    """Compute the sets of valid paths for an EIP712 schema."""

    def append_paths(
        path: str, current_type: list[NameType], types: dict[str, list[NameType]], paths: set[str]
    ) -> None:
        for domain in current_type:
            new_path = _append_path(path, domain["name"])
            type = domain["type"]
            if domain["type"].endswith(ARRAY_SUFFIX):
                type = _remove_slicing(type)
                new_path += ARRAY_SUFFIX
            if type in types:
                append_paths(new_path, types[type], types, paths)
            else:
                paths.add(new_path)

    if schema.primaryType not in schema.types:
        raise ValueError(f"Invalid schema: primaryType {schema.primaryType} not in types")
    paths: set[str] = set()
    append_paths("", schema.types[schema.primaryType], schema.types, paths)
    return paths


@dataclass(kw_only=True)
class FormatPaths:
    data_paths: set[str]  # References to values in the serialized data
    format_paths: set[str]  # References to values in the format specification file
    container_paths: set[str]  # References to values in the container


def compute_format_paths(format: Format) -> FormatPaths:
    """Compute the sets of paths referred in an ERC7730 Format."""
    paths = FormatPaths(data_paths=set(), format_paths=set(), container_paths=set())

    def add_path(root: str, path: str) -> None:
        if path.startswith("@."):
            paths.container_paths.add(path[2:])
        elif path.startswith("$."):
            paths.format_paths.add(path[2:])
        elif path.startswith("#."):
            paths.data_paths.add(path[2:])
        else:
            paths.data_paths.add(_append_path(root, path))

    def append_paths(path: str, fields: Field | None) -> None:
        if fields is not None:
            field = fields.root
            field_name = ""
            match field:
                case Reference():
                    pass
                case FieldDescription():
                    field_name = field.label
                    add_path(path, field_name)
                    if field.params and isinstance(field.params, TokenAmountParameters):  # FIXME model is not correct
                        add_path(path, _remove_slicing(field.params.tokenPath))
                case NestedFields():
                    field_name = field.path
                    append_paths(_append_path(path, field_name), field.fields)  # type: ignore

    if format.fields is not None:
        for f in format.fields:
            append_paths("", f)
    return paths
