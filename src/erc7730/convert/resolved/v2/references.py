import json
from typing import Any

from pydantic import TypeAdapter

from erc7730.common.output import OutputAdder
from erc7730.common.pydantic import model_to_json_str
from erc7730.convert.resolved.v2.constants import ConstantProvider
from erc7730.convert.resolved.v2.parameters import resolve_field_parameters
from erc7730.convert.resolved.v2.values import resolve_field_value
from erc7730.model.input.v2.display import (
    InputFieldDefinition,
    InputFieldParameters,
    InputReference,
)
from erc7730.model.input.v2.format import FieldFormat
from erc7730.model.paths import DataPath, DescriptorPath, Field
from erc7730.model.paths.path_ops import descriptor_path_strip_prefix
from erc7730.model.resolved.display import ResolvedValueConstant, ResolvedValuePath
from erc7730.model.resolved.metadata import EnumDefinition
from erc7730.model.resolved.v2.display import (
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFieldParameters,
)
from erc7730.model.types import Id

DEFINITIONS_PATH = DescriptorPath(elements=[Field(identifier="display"), Field(identifier="definitions")])


def resolve_reference(
    prefix: DataPath,
    reference: InputReference,
    definitions: dict[Id, InputFieldDefinition],
    enums: dict[Id, EnumDefinition],
    constants: ConstantProvider,
    out: OutputAdder,
) -> ResolvedField | None:
    if (definition := _get_definition(reference.ref, definitions, out)) is None:
        return None

    if (label := definition.label) is None:
        return out.error(
            title="Missing display field label",
            message=f"Label must be defined on the referenced display field definition {reference.ref}.",
        )

    params: dict[str, Any] = {}
    if (definition_params := definition.params) is not None:
        params.update(json.loads(model_to_json_str(definition_params)))
    if (reference_params := reference.params) is not None:
        params.update(reference_params)

    resolved_params: ResolvedFieldParameters | None = None

    if params:
        input_params: InputFieldParameters = TypeAdapter(InputFieldParameters).validate_json(json.dumps(params))
        if (resolved_params := resolve_field_parameters(prefix, input_params, enums, constants, out)) is None:
            return None

    if (value_or_path := resolve_field_value(prefix, reference, definition.format, constants, out)) is None:
        return None

    # Build field dict for model_validate to handle aliases and discriminated unions
    field_dict: dict[str, Any] = {
        "label": str(constants.resolve(label, out)),
        "format": FieldFormat(definition.format) if definition.format is not None else None,
    }

    if resolved_params is not None:
        field_dict["params"] = resolved_params.model_dump(by_alias=True, exclude_none=True)

    # Set either path or value based on the ResolvedValue type
    if isinstance(value_or_path, ResolvedValuePath):
        field_dict["path"] = str(value_or_path.path)
    elif isinstance(value_or_path, ResolvedValueConstant):
        field_dict["value"] = value_or_path.value

    return ResolvedFieldDescription.model_validate(field_dict)


def _get_definition(
    ref: DescriptorPath, definitions: dict[Id, InputFieldDefinition], out: OutputAdder
) -> InputFieldDefinition | None:
    if (definition_id := _get_definition_id(ref, out)) is None:
        return None

    if (definition := definitions.get(definition_id)) is None:
        return out.error(
            title="Invalid display definition reference",
            message=f"""Display definition "{definition_id}" does not exist, valid ones are: """
            f"{', '.join(definitions.keys())}.",
        )
    return definition


def _get_definition_id(ref: DescriptorPath, out: OutputAdder) -> Id | None:
    try:
        tail = descriptor_path_strip_prefix(ref, DEFINITIONS_PATH)
    except ValueError:
        return out.error(
            title="Invalid definition reference path",
            message=f"References to display field definitions are restricted to {DEFINITIONS_PATH}, {ref} "
            f"cannot be used as a field definition reference.",
        )
    if len(tail.elements) != 1:
        return out.error(
            title="Invalid definition reference path",
            message=f"References to display field definitions are restricted to fields immediately under "
            f"{DEFINITIONS_PATH}, deep nesting is not allowed, {ref} cannot be used as a field "
            f"definition reference.",
        )
    if not isinstance(element := tail.elements[0], Field):
        return out.error(
            title="Invalid definition reference path",
            message=f"References to display field definitions are restricted to fields immediately under "
            f"{DEFINITIONS_PATH}, array operators are not allowed, {ref} cannot be used as a field "
            f"definition reference.",
        )

    return element.identifier
