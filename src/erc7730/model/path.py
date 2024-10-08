from enum import StrEnum, auto
from typing import Annotated, Any, Literal, Self

from lark import Lark, UnexpectedInput
from lark.exceptions import VisitError
from lark.visitors import Transformer_InPlaceRecursive
from pydantic import Field as PydanticField
from pydantic import (
    TypeAdapter,
    ValidationError,
    model_validator,
)

from erc7730.model.base import Model

ArrayIndex = Annotated[
    int,
    PydanticField(
        title="Array index",
        description="Index of an element in an array. An index can be negative to count from the end of the array.",
        ge=-32767,  # TODO to be refined
        le=32768,  # TODO to be refined
    ),
]


class Field(Model):
    """A path component designating a field in a structured data schema."""

    type: Literal["field"] = PydanticField(
        "field",
        title="Path Component Type",
        description="The path component type identifier (discriminator for path components discriminated union).",
    )

    identifier: str = PydanticField(
        title="Field Identifier",
        description="The identifier of the referenced field in the structured data schema.",
        pattern=r"^[a-zA-Z0-9_]+$",
    )

    def __str__(self) -> str:
        return self.identifier


class ArrayElement(Model):
    """A path component designating a single element of an array."""

    type: Literal["array_element"] = PydanticField(
        "array_element",
        title="Path Component Type",
        description="The path component type identifier (discriminator for path components discriminated union).",
    )

    index: ArrayIndex = PydanticField(
        title="Array Element",
        description="The index of the element in the array. It can be negative to count from the end of the array.",
    )

    def __str__(self) -> str:
        return f"[{self.index}]"


class ArraySlice(Model):
    """A path component designating an element range of an array (in which case, the path targets multiple values)."""

    type: Literal["array_slice"] = PydanticField(
        "array_slice",
        title="Path Component Type",
        description="The path component type identifier (discriminator for path components discriminated union).",
    )

    start: ArrayIndex = PydanticField(
        title="Slice Start Index",
        description="The start index of the slice. Must be positive and lower than the end index.",
        ge=0,
    )

    end: ArrayIndex = PydanticField(
        title="Slice End Index",
        description="The end index of the slice. Must be positive and greater than the start index.",
        ge=0,
    )

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.start > self.end:
            raise ValueError("Array slice start index must be lower than end index.")
        return self

    def __str__(self) -> str:
        return f"[{self.start}:{self.end}]"


class Array(Model):
    """A path component designating all elements of an array (in which case, the path targets multiple values)."""

    type: Literal["array"] = PydanticField(
        "array",
        title="Path Component Type",
        description="The path component type identifier (discriminator for path components discriminated union).",
    )

    def __str__(self) -> str:
        return "[]"


class ContainerField(StrEnum):
    """
    Path applying to the container of the structured data to be signed.

    Such paths are prefixed with "@".
    """

    VALUE = auto()
    """The native currency value of the transaction containing the structured data."""

    FROM = auto()
    """The address of the sender of the transaction / signer of the message."""

    TO = auto()
    """The destination address of the containing transaction, ie the target smart contract address."""


DataPathElement = Annotated[
    Field | ArrayElement | ArraySlice | Array,
    PydanticField(
        title="Data Path Element",
        description="An element of a data path, applying to the structured data schema (ABI path for contracts, path"
        "in the message types itself for EIP-712)",
        discriminator="type",
    ),
]


DescriptorPathElement = Annotated[
    Field | ArrayElement,
    PydanticField(
        title="Descriptor Path Element",
        description="An element of a descriptor path, applying to the current file describing the structured data"
        "formatting, after merging with includes.",
        discriminator="type",
    ),
]


class ContainerPath(Model):
    """
    Path applying to the container of the structured data to be signed.

    Such paths are prefixed with "@".
    """

    type: Literal["container"] = PydanticField(
        "container",
        title="Path Type",
        description="The path type identifier (discriminator for paths discriminated union).",
    )

    field: ContainerField = PydanticField(
        title="Container field",
        description="The referenced field in the container, only some well-known values are allowed.",
    )

    def __str__(self) -> str:
        return f"@.{self.field}"


class DataPath(Model):
    """
    Path applying to the structured data schema (ABI path for contracts, path in the message types itself for
    EIP-712).

    A data path can reference multiple values if it contains array elements or slices.

    Such paths are prefixed with "#".
    """

    type: Literal["data"] = PydanticField(
        "data", title="Path Type", description="The path type identifier (discriminator for paths discriminated union)."
    )

    absolute: bool = PydanticField(
        title="Absolute",
        description="Whether the path is absolute (starting from the structured data root) or relative (starting from"
        "the current field).",
    )

    elements: list[DataPathElement] = PydanticField(
        title="Elements",
        description="The path elements, as a list of references to be interpreted left to right from the structured"
        "data root to reach the referenced value(s).",
        min_length=1,
    )

    def __str__(self) -> str:
        return f'{"#." if self.absolute else ""}{".".join(str(e) for e in self.elements)}'


class DescriptorPath(Model):
    """
    Path applying to the current file describing the structured data formatting, after merging with includes.

    A descriptor path can only reference a single value in the document.

    Such paths are prefixed with "$".
    """

    type: Literal["descriptor"] = PydanticField(
        "descriptor",
        title="Path Type",
        description="The path type identifier (discriminator for paths discriminated union).",
    )

    elements: list[DescriptorPathElement] = PydanticField(
        title="Elements",
        description="The path elements, as a list of references to be interpreted left to right from the current file"
        "root to reach the referenced value.",
        min_length=1,
    )

    def __str__(self) -> str:
        return f'$.{".".join(str(e) for e in self.elements)}'


PATH_PARSER = Lark(
    grammar=r"""
        ?path: descriptor_path | container_path | data_path
    
        descriptor_path: "$." descriptor_path_component ("." descriptor_path_component)*
        ?descriptor_path_component: field | array_element
    
        container_path: "@." container_field
        !container_field: "from" | "to" | "value"
    
        ?data_path: absolute_data_path | relative_data_path
        absolute_data_path: "#." data_path_component ("." data_path_component)*
        relative_data_path: data_path_component ("." data_path_component)*
        ?data_path_component: field | array | array_element | array_slice

        field: /[a-zA-Z0-9_]+/
        array: "[]"
        array_index: /-?[0-9]+/
        array_element: "[" array_index "]"
        array_slice: "[" array_index ":" array_index "]"
    """,
    start="path",
)


class PathTransformer(Transformer_InPlaceRecursive):
    """Visitor to transform the parsed path AST into path domain model objects."""

    def field(self, ast: Any) -> Field:
        (value,) = ast
        return Field(identifier=value.value)

    def array(self, ast: Any) -> Array:
        return Array()

    def array_index(self, ast: Any) -> ArrayIndex:
        (value,) = ast
        return TypeAdapter(ArrayIndex).validate_strings(value)

    def array_element(self, ast: Any) -> ArrayElement:
        (value,) = ast
        return ArrayElement(index=value)

    def array_slice(self, ast: Any) -> ArraySlice:
        (start, end) = ast
        return ArraySlice(start=start, end=end)

    def container_field(self, ast: Any) -> ContainerField:
        (value,) = ast
        return ContainerField(value)

    def descriptor_path(self, ast: Any) -> DescriptorPath:
        return DescriptorPath(elements=ast)

    def container_path(self, ast: Any) -> ContainerPath:
        (value,) = ast
        return ContainerPath(field=value)

    def absolute_data_path(self, ast: Any) -> DataPath:
        return DataPath(elements=ast, absolute=True)

    def relative_data_path(self, ast: Any) -> DataPath:
        return DataPath(elements=ast, absolute=False)


PATH_TRANSFORMER = PathTransformer()


def parse_path(path: str) -> ContainerPath | DataPath | DescriptorPath:
    """
    Parse a path string into a domain model object.

    :param path: the path input string
    :return: an union of all possible path types
    :raises ValueError: if the input string is not a valid path
    :raises Exception: if the path parsing fails for an unexpected reason
    """
    try:
        return PATH_TRANSFORMER.transform(PATH_PARSER.parse(path))
    except UnexpectedInput as e:
        # TODO improve error reporting, see:
        #  https://github.com/lark-parser/lark/blob/master/examples/advanced/error_reporting_lalr.py
        raise ValueError(f"""Invalid path "{path}": {e}""") from None
    except VisitError as e:
        if isinstance(e.orig_exc, ValidationError):
            raise ValueError(f"""Invalid path "{path}": {e.orig_exc}`""") from None
        raise Exception(
            f"""Failed to parse path "{path}": {e}`\n"""
            "This is most likely a bug in the ERC-7730 library, please report it to authors."
        ) from e
    except Exception as e:
        raise Exception(
            f"""Failed to parse path "{path}": {e}`\n"""
            "This is most likely a bug in the ERC-7730 library, please report it to authors."
        ) from e
