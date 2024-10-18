from typing import assert_never, final, override

from pydantic import RootModel
from pydantic_string_url import HttpUrl

from erc7730.common import client
from erc7730.common.output import OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.convert.resolved.parameters import convert_field_parameters
from erc7730.convert.resolved.references import convert_reference
from erc7730.model.abi import ABI
from erc7730.model.context import EIP712JsonSchema
from erc7730.model.display import (
    FieldFormat,
)
from erc7730.model.input.context import InputContract, InputContractContext, InputEIP712, InputEIP712Context
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import (
    InputDisplay,
    InputField,
    InputFieldDefinition,
    InputFieldDescription,
    InputFormat,
    InputNestedFields,
    InputReference,
)
from erc7730.model.paths import ROOT_DATA_PATH, ContainerPath, DataPath
from erc7730.model.paths.path_ops import data_or_container_path_concat, data_path_concat
from erc7730.model.resolved.context import (
    ResolvedContract,
    ResolvedContractContext,
    ResolvedEIP712,
    ResolvedEIP712Context,
)
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.display import (
    ResolvedDisplay,
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFormat,
    ResolvedNestedFields,
)


@final
class ERC7730InputToResolved(ERC7730Converter[InputERC7730Descriptor, ResolvedERC7730Descriptor]):
    """
    Converts ERC-7730 descriptor input to resolved form.

    After conversion, the descriptor is in resolved form:
     - URLs have been fetched
     - Contract addresses have been normalized to lowercase (TODO not implemented)
     - References have been inlined
     - Constants have been inlined (TODO not implemented)
     - Field definitions have been inlined
     - Selectors have been converted to 4 bytes form (TODO not implemented)
    """

    @override
    def convert(self, descriptor: InputERC7730Descriptor, out: OutputAdder) -> ResolvedERC7730Descriptor | None:
        context = self._convert_context(descriptor.context, out)
        display = self._convert_display(descriptor.display, out)

        if context is None or display is None:
            return None

        return ResolvedERC7730Descriptor.model_validate(
            {"$schema": descriptor.schema_, "context": context, "metadata": descriptor.metadata, "display": display}
        )

    @classmethod
    def _convert_context(
        cls, context: InputContractContext | InputEIP712Context, out: OutputAdder
    ) -> ResolvedContractContext | ResolvedEIP712Context | None:
        if isinstance(context, InputContractContext):
            return cls._convert_context_contract(context, out)

        if isinstance(context, InputEIP712Context):
            return cls._convert_context_eip712(context, out)

        return out.error(
            title="Invalid context type",
            message=f"Descriptor has an invalid context type: {type(context)}. Context type should be either contract"
            f"or eip712.",
        )

    @classmethod
    def _convert_context_contract(
        cls, context: InputContractContext, out: OutputAdder
    ) -> ResolvedContractContext | None:
        contract = cls._convert_contract(context.contract, out)

        if contract is None:
            return None

        return ResolvedContractContext(contract=contract)

    @classmethod
    def _convert_contract(cls, contract: InputContract, out: OutputAdder) -> ResolvedContract | None:
        abi = cls._convert_abis(contract.abi, out)

        if abi is None:
            return None

        return ResolvedContract(
            abi=abi, deployments=contract.deployments, addressMatcher=contract.addressMatcher, factory=contract.factory
        )

    @classmethod
    def _convert_abis(cls, abis: list[ABI] | HttpUrl, out: OutputAdder) -> list[ABI] | None:
        if isinstance(abis, HttpUrl):
            return client.get(abis, RootModel[list[ABI]]).root

        if isinstance(abis, list):
            return abis

        return out.error(
            title="Invalid ABIs type",
            message=f"Descriptor contains invalid value for ABIs: {type(abis)}, it should either be an URL or a JSON"
            f"representation of the ABIs.",
        )

    @classmethod
    def _convert_context_eip712(cls, context: InputEIP712Context, out: OutputAdder) -> ResolvedEIP712Context | None:
        eip712 = cls._convert_eip712(context.eip712, out)

        if eip712 is None:
            return None

        return ResolvedEIP712Context(eip712=eip712)

    @classmethod
    def _convert_eip712(cls, eip712: InputEIP712, out: OutputAdder) -> ResolvedEIP712 | None:
        schemas = cls._convert_schemas(eip712.schemas, out)

        if schemas is None:
            return None

        return ResolvedEIP712(
            domain=eip712.domain,
            schemas=schemas,
            domainSeparator=eip712.domainSeparator,
            deployments=eip712.deployments,
        )

    @classmethod
    def _convert_schemas(
        cls, schemas: list[EIP712JsonSchema | HttpUrl], out: OutputAdder
    ) -> list[EIP712JsonSchema] | None:
        resolved_schemas = []
        for schema in schemas:
            if (resolved_schema := cls._convert_schema(schema, out)) is not None:
                resolved_schemas.append(resolved_schema)
        return resolved_schemas

    @classmethod
    def _convert_schema(cls, schema: EIP712JsonSchema | HttpUrl, out: OutputAdder) -> EIP712JsonSchema | None:
        if isinstance(schema, HttpUrl):
            return client.get(schema, EIP712JsonSchema)

        if isinstance(schema, EIP712JsonSchema):
            return schema

        return out.error(
            title="Invalid EIP-712 schema type",
            message=f"Descriptor contains invalid value for EIP-712 schema: {type(schema)}, it should either be an URL "
            f"or a JSON representation of the schema.",
        )

    @classmethod
    def _convert_display(cls, display: InputDisplay, out: OutputAdder) -> ResolvedDisplay | None:
        formats = {}
        for format_key, format in display.formats.items():
            if (resolved_format := cls._convert_format(format, display.definitions or {}, out)) is not None:
                formats[format_key] = resolved_format

        return ResolvedDisplay(formats=formats)

    @classmethod
    def _convert_field_description(
        cls, prefix: DataPath, definition: InputFieldDescription, out: OutputAdder
    ) -> ResolvedFieldDescription | None:
        params = convert_field_parameters(definition.params, out) if definition.params is not None else None

        return ResolvedFieldDescription.model_validate(
            {
                "$id": definition.id,
                "path": data_or_container_path_concat(prefix, definition.path),
                "label": definition.label,
                "format": FieldFormat(definition.format) if definition.format is not None else None,
                "params": params,
            }
        )

    @classmethod
    def _convert_format(
        cls, format: InputFormat, definitions: dict[str, InputFieldDefinition], out: OutputAdder
    ) -> ResolvedFormat | None:
        fields = cls._convert_fields(ROOT_DATA_PATH, format.fields, definitions, out)

        if fields is None:
            return None

        return ResolvedFormat.model_validate(
            {
                "$id": format.id,
                "intent": format.intent,
                "fields": fields,
                "required": format.required,
                "excluded": format.excluded,
                "screens": format.screens,
            }
        )

    @classmethod
    def _convert_fields(
        cls,
        prefix: DataPath,
        fields: list[InputField],
        definitions: dict[str, InputFieldDefinition],
        out: OutputAdder,
    ) -> list[ResolvedField] | None:
        resolved_fields = []
        for input_format in fields:
            if (resolved_field := cls._convert_field(prefix, input_format, definitions, out)) is None:
                return None
            resolved_fields.append(resolved_field)
        return resolved_fields

    @classmethod
    def _convert_field(
        cls, prefix: DataPath, field: InputField, definitions: dict[str, InputFieldDefinition], out: OutputAdder
    ) -> ResolvedField | None:
        match field:
            case InputReference():
                return convert_reference(field, definitions, out)
            case InputFieldDescription():
                return cls._convert_field_description(prefix, field, out)
            case InputNestedFields():
                return cls._convert_nested_fields(prefix, field, definitions, out)
            case _:
                assert_never(field)

    @classmethod
    def _convert_nested_fields(
        cls,
        prefix: DataPath,
        fields: InputNestedFields,
        definitions: dict[str, InputFieldDefinition],
        out: OutputAdder,
    ) -> ResolvedNestedFields | None:
        path: DataPath
        match fields.path:
            case DataPath() as p:
                path = data_path_concat(prefix, p)
            case ContainerPath() as p:
                return out.error(
                    title="Invalid path type",
                    message=f"Container path {p} cannot be used with nested fields.",
                )
            case _:
                assert_never(fields.path)

        resolved_fields = cls._convert_fields(prefix, fields.fields, definitions, out)

        if resolved_fields is None:
            return None

        return ResolvedNestedFields(path=path, fields=resolved_fields)
