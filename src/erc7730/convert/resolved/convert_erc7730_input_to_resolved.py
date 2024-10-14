from typing import final, override

from pydantic import RootModel
from pydantic_string_url import HttpUrl

from erc7730.common import client
from erc7730.common.output import OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.convert.resolved.references import convert_reference
from erc7730.model.abi import ABI
from erc7730.model.context import EIP712JsonSchema
from erc7730.model.display import (
    AddressNameParameters,
    CallDataParameters,
    DateParameters,
    FieldFormat,
    NftNameParameters,
    TokenAmountParameters,
    UnitParameters,
)
from erc7730.model.input.context import InputContract, InputContractContext, InputEIP712, InputEIP712Context
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import (
    InputDisplay,
    InputEnumParameters,
    InputField,
    InputFieldDefinition,
    InputFieldDescription,
    InputFieldParameters,
    InputFormat,
    InputNestedFields,
    InputReference,
)
from erc7730.model.resolved.context import (
    ResolvedContract,
    ResolvedContractContext,
    ResolvedEIP712,
    ResolvedEIP712Context,
)
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.display import (
    ResolvedDisplay,
    ResolvedEnumParameters,
    ResolvedField,
    ResolvedFieldDefinition,
    ResolvedFieldDescription,
    ResolvedFieldParameters,
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
        definitions: dict[str, ResolvedFieldDefinition] = {}
        if display.definitions is not None:
            for definition_key, definition in display.definitions.items():
                if (resolved_definition := cls._convert_field_definition(definition, out)) is not None:
                    definitions[definition_key] = resolved_definition

        formats = {}
        for format_key, format in display.formats.items():
            if (resolved_format := cls._convert_format(format, definitions, out)) is not None:
                formats[format_key] = resolved_format

        return ResolvedDisplay(formats=formats)

    @classmethod
    def _convert_field_definition(
        cls, definition: InputFieldDefinition, out: OutputAdder
    ) -> ResolvedFieldDefinition | None:
        params = cls._convert_field_parameters(definition.params, out) if definition.params is not None else None

        return ResolvedFieldDefinition.model_validate(
            {
                "$id": definition.id,
                "label": definition.label,
                "format": FieldFormat(definition.format) if definition.format is not None else None,
                "params": params,
            }
        )

    @classmethod
    def _convert_field_description(
        cls, definition: InputFieldDescription, out: OutputAdder
    ) -> ResolvedFieldDescription | None:
        params = cls._convert_field_parameters(definition.params, out) if definition.params is not None else None

        return ResolvedFieldDescription.model_validate(
            {
                "$id": definition.id,
                "path": definition.path,
                "label": definition.label,
                "format": FieldFormat(definition.format) if definition.format is not None else None,
                "params": params,
            }
        )

    @classmethod
    def _convert_field_parameters(
        cls, params: InputFieldParameters, out: OutputAdder
    ) -> ResolvedFieldParameters | None:
        if isinstance(params, AddressNameParameters):
            return params
        if isinstance(params, CallDataParameters):
            return params
        if isinstance(params, TokenAmountParameters):
            return params
        if isinstance(params, NftNameParameters):
            return params
        if isinstance(params, DateParameters):
            return params
        if isinstance(params, UnitParameters):
            return params
        if isinstance(params, InputEnumParameters):
            return cls._convert_enum_parameters(params, out)
        return out.error(title="Invalid field parameters", message=f"Invalid field parameters type: {type(params)}")

    @classmethod
    def _convert_enum_parameters(cls, params: InputEnumParameters, out: OutputAdder) -> ResolvedEnumParameters | None:
        return ResolvedEnumParameters.model_validate({"$ref": params.ref})  # TODO must inline here

    @classmethod
    def _convert_format(
        cls, format: InputFormat, definitions: dict[str, ResolvedFieldDefinition], error: OutputAdder
    ) -> ResolvedFormat | None:
        fields = cls._convert_fields(format.fields, definitions, error)

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
        cls, fields: list[InputField], definitions: dict[str, ResolvedFieldDefinition], out: OutputAdder
    ) -> list[ResolvedField] | None:
        resolved_fields = []
        for input_format in fields:
            if (resolved_field := cls._convert_field(input_format, definitions, out)) is not None:
                resolved_fields.append(resolved_field)
        return resolved_fields

    @classmethod
    def _convert_field(
        cls, field: InputField, definitions: dict[str, ResolvedFieldDefinition], out: OutputAdder
    ) -> ResolvedField | None:
        if isinstance(field, InputReference):
            return convert_reference(field, definitions, out)
        if isinstance(field, InputFieldDescription):
            return cls._convert_field_description(field, out)
        if isinstance(field, InputNestedFields):
            return cls._convert_nested_fields(field, definitions, out)
        return out.error(title="Invalid field type", message=f"Invalid field type: {type(field)}")

    @classmethod
    def _convert_nested_fields(
        cls, fields: InputNestedFields, definitions: dict[str, ResolvedFieldDefinition], out: OutputAdder
    ) -> ResolvedNestedFields | None:
        resolved_fields = cls._convert_fields(fields.fields, definitions, out)

        if resolved_fields is None:
            return None

        return ResolvedNestedFields(path=fields.path, fields=resolved_fields)
