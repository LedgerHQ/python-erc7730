from typing import final, override

import requests
from pydantic import AnyUrl, RootModel

from erc7730.convert import ERC7730Converter
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
    """Converts ERC-7730 descriptor input to resolved form."""

    @override
    def convert(
        self, descriptor: InputERC7730Descriptor, error: ERC7730Converter.ErrorAdder
    ) -> ResolvedERC7730Descriptor | None:
        context = self._convert_context(descriptor.context, error)
        display = self._convert_display(descriptor.display, error)

        if context is None or display is None:
            return None

        return ResolvedERC7730Descriptor.model_validate(
            {"$schema": descriptor.schema_, "context": context, "metadata": descriptor.metadata, "display": display}
        )

    @classmethod
    def _convert_context(
        cls, context: InputContractContext | InputEIP712Context, error: ERC7730Converter.ErrorAdder
    ) -> ResolvedContractContext | ResolvedEIP712Context | None:
        if isinstance(context, InputContractContext):
            return cls._convert_context_contract(context, error)

        if isinstance(context, InputEIP712Context):
            return cls._convert_context_eip712(context, error)

        return error.error(f"Invalid context type: {type(context)}")

    @classmethod
    def _convert_context_contract(
        cls, context: InputContractContext, error: ERC7730Converter.ErrorAdder
    ) -> ResolvedContractContext | None:
        contract = cls._convert_contract(context.contract, error)

        if contract is None:
            return None

        return ResolvedContractContext(contract=contract)

    @classmethod
    def _convert_contract(cls, contract: InputContract, error: ERC7730Converter.ErrorAdder) -> ResolvedContract | None:
        abi = cls._convert_abis(contract.abi, error)

        if abi is None:
            return None

        return ResolvedContract(
            abi=abi, deployments=contract.deployments, addressMatcher=contract.addressMatcher, factory=contract.factory
        )

    @classmethod
    def _convert_abis(cls, abis: list[ABI] | AnyUrl, error: ERC7730Converter.ErrorAdder) -> list[ABI] | None:
        if isinstance(abis, AnyUrl):
            resp = requests.get(cls._adapt_uri(abis), timeout=10)  # type:ignore
            resp.raise_for_status()
            return RootModel[list[ABI]].model_validate(resp.json()).root

        if isinstance(abis, list):
            return abis

        return error.error(f"Invalid ABIs type: {type(abis)}")

    @classmethod
    def _convert_context_eip712(
        cls, context: InputEIP712Context, error: ERC7730Converter.ErrorAdder
    ) -> ResolvedEIP712Context | None:
        eip712 = cls._convert_eip712(context.eip712, error)

        if eip712 is None:
            return None

        return ResolvedEIP712Context(eip712=eip712)

    @classmethod
    def _convert_eip712(cls, eip712: InputEIP712, error: ERC7730Converter.ErrorAdder) -> ResolvedEIP712 | None:
        schemas = cls._convert_schemas(eip712.schemas, error)

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
        cls, schemas: list[EIP712JsonSchema | AnyUrl], error: ERC7730Converter.ErrorAdder
    ) -> list[EIP712JsonSchema] | None:
        resolved_schemas = []
        for schema in schemas:
            if (resolved_schema := cls._convert_schema(schema, error)) is not None:
                resolved_schemas.append(resolved_schema)
        return resolved_schemas

    @classmethod
    def _convert_schema(
        cls, schema: EIP712JsonSchema | AnyUrl, error: ERC7730Converter.ErrorAdder
    ) -> EIP712JsonSchema | None:
        if isinstance(schema, AnyUrl):
            resp = requests.get(cls._adapt_uri(schema), timeout=10)  # type:ignore
            resp.raise_for_status()
            return EIP712JsonSchema.model_validate(resp.json())

        if isinstance(schema, EIP712JsonSchema):
            return schema

        return error.error(f"Invalid EIP-712 schema type: {type(schema)}")

    @classmethod
    def _convert_display(cls, display: InputDisplay, error: ERC7730Converter.ErrorAdder) -> ResolvedDisplay | None:
        if display.definitions is None:
            definitions = None
        else:
            definitions = {}
            for definition_key, definition in display.definitions.items():
                if (resolved_definition := cls._convert_field_definition(definition, error)) is not None:
                    definitions[definition_key] = resolved_definition

        formats = {}
        for format_key, format in display.formats.items():
            if (resolved_format := cls._convert_format(format, error)) is not None:
                formats[format_key] = resolved_format

        return ResolvedDisplay(definitions=definitions, formats=formats)

    @classmethod
    def _convert_field_definition(
        cls, definition: InputFieldDefinition, error: ERC7730Converter.ErrorAdder
    ) -> ResolvedFieldDefinition | None:
        params = cls._convert_field_parameters(definition.params, error) if definition.params is not None else None

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
        cls, definition: InputFieldDescription, error: ERC7730Converter.ErrorAdder
    ) -> ResolvedFieldDescription | None:
        params = cls._convert_field_parameters(definition.params, error) if definition.params is not None else None

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
        cls, params: InputFieldParameters, error: ERC7730Converter.ErrorAdder
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
            return cls._convert_enum_parameters(params, error)
        return error.error(f"Invalid field parameters type: {type(params)}")

    @classmethod
    def _convert_enum_parameters(
        cls, params: InputEnumParameters, error: ERC7730Converter.ErrorAdder
    ) -> ResolvedEnumParameters | None:
        return ResolvedEnumParameters.model_validate({"$ref": params.ref})  # TODO must inline here

    @classmethod
    def _convert_format(cls, format: InputFormat, error: ERC7730Converter.ErrorAdder) -> ResolvedFormat | None:
        fields = cls._convert_fields(format.fields, error)

        if fields is None:
            return None

        return ResolvedFormat.model_validate(
            {
                "$id": format.id,
                "intent": format.intent,
                "fields": fields,
                "required": format.required,
                "screens": format.screens,
            }
        )

    @classmethod
    def _convert_fields(
        cls, fields: list[InputField], error: ERC7730Converter.ErrorAdder
    ) -> list[ResolvedField] | None:
        resolved_fields = []
        for input_format in fields:
            if (resolved_field := cls._convert_field(input_format, error)) is not None:
                resolved_fields.append(resolved_field)
        return resolved_fields

    @classmethod
    def _convert_field(cls, field: InputField, error: ERC7730Converter.ErrorAdder) -> ResolvedField | None:
        if isinstance(field, InputReference):
            return cls._convert_reference(field, error)
        if isinstance(field, InputFieldDescription):
            return cls._convert_field_description(field, error)
        if isinstance(field, InputNestedFields):
            return cls._convert_nested_fields(field, error)
        return error.error(f"Invalid field type: {type(field)}")

    @classmethod
    def _convert_nested_fields(
        cls, fields: InputNestedFields, error: ERC7730Converter.ErrorAdder
    ) -> ResolvedNestedFields | None:
        resolved_fields = cls._convert_fields(fields.fields, error)

        if resolved_fields is None:
            return None

        return ResolvedNestedFields(path=fields.path, fields=resolved_fields)

    @classmethod
    def _convert_reference(cls, reference: InputReference, error: ERC7730Converter.ErrorAdder) -> ResolvedField | None:
        raise NotImplementedError()  # TODO

    @classmethod
    def _adapt_uri(cls, url: AnyUrl) -> AnyUrl:
        return AnyUrl(
            str(url).replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/")
        )
