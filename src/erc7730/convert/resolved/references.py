from typing import Any

from pydantic import RootModel

from erc7730.common.options import first_not_none
from erc7730.common.output import OutputAdder
from erc7730.common.pydantic import model_to_json_dict
from erc7730.convert.resolved.paths import strip_prefix
from erc7730.model.display import (
    FieldFormat,
)
from erc7730.model.input.display import (
    InputReference,
)
from erc7730.model.input.path import InputPath
from erc7730.model.path import DescriptorPath, Field
from erc7730.model.resolved.display import (
    ResolvedField,
    ResolvedFieldDefinition,
    ResolvedFieldDescription,
    ResolvedFieldParameters,
)

DEFINITIONS_PATH = DescriptorPath(elements=[Field(identifier="display"), Field(identifier="definitions")])


def convert_reference(
    reference: InputReference, definitions: dict[str, ResolvedFieldDefinition], out: OutputAdder
) -> ResolvedField | None:
    if (definition := _get_definition(reference.ref, definitions, out)) is None:
        return None

    if (label := first_not_none(reference.label, definition.label)) is None:
        return out.error(
            title="Missing display field label",
            message=f"Label must be defined either on display field, or on the referenced display field definition "
            f"{reference.ref}.",
        )

    params: dict[str, Any] = {}
    if (definition_params := definition.params) is not None:
        params.update(model_to_json_dict(definition_params))
    if (reference_params := reference.params) is not None:
        params.update(reference_params)

    resolved_params: ResolvedFieldParameters | None = (
        RootModel(ResolvedFieldParameters).model_validate(params).root if params else None  # type:ignore
    )

    return ResolvedFieldDescription(
        path=reference.path,
        label=label,
        format=FieldFormat(definition.format),
        params=resolved_params,
    )


def _get_definition(
    ref: InputPath, definitions: dict[str, ResolvedFieldDefinition], out: OutputAdder
) -> ResolvedFieldDefinition | None:
    if (definition_id := _get_definition_id(ref, out)) is None:
        return None

    if (definition := definitions.get(definition_id)) is None:
        return out.error(
            title="Invalid display definition reference",
            message=f"""Display definition "{definition_id}" does not exist, valid ones are: """
            f"{', '.join(definitions.keys())}.",
        )
    return definition


def _get_definition_id(ref: InputPath, out: OutputAdder) -> str | None:
    if not isinstance(ref, DescriptorPath):
        return out.error(
            title="Invalid definition reference path type",
            message=f"""Reference to a definition must be a descriptor path starting with "$.", got {ref}.""",
        )

    try:
        tail = strip_prefix(ref, DEFINITIONS_PATH)
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
