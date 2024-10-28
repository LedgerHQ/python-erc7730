from typing import assert_never, final, override

from eip712.model.schema import EIP712Type
from pydantic_string_url import HttpUrl

from erc7730.common import client
from erc7730.common.abi import reduce_signature, signature_to_selector
from erc7730.common.output import OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.convert.resolved.constants import ConstantProvider, DefaultConstantProvider
from erc7730.convert.resolved.parameters import resolve_field_parameters
from erc7730.convert.resolved.references import resolve_reference
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
from erc7730.model.input.metadata import InputMetadata
from erc7730.model.metadata import EnumDefinition
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
from erc7730.model.resolved.metadata import ResolvedMetadata
from erc7730.model.types import Id, Selector


@final
class ERC7730InputToResolved(ERC7730Converter[InputERC7730Descriptor, ResolvedERC7730Descriptor]):
    """
    Converts ERC-7730 descriptor input to resolved form.

    After conversion, the descriptor is in resolved form:
     - URLs have been fetched
     - Contract addresses have been normalized to lowercase (TODO not implemented)
     - References have been inlined
     - Constants have been inlined
     - Field definitions have been inlined
     - Selectors have been converted to 4 bytes form
    """

    @override
    def convert(self, descriptor: InputERC7730Descriptor, out: OutputAdder) -> ResolvedERC7730Descriptor | None:
        constants = DefaultConstantProvider(descriptor)

        if (context := self._resolve_context(descriptor.context, out)) is None:
            return None
        if (metadata := self._resolve_metadata(descriptor.metadata, out)) is None:
            return None
        if (
            display := self._resolve_display(descriptor.display, context, metadata.enums or {}, constants, out)
        ) is None:
            return None

        return ResolvedERC7730Descriptor(context=context, metadata=metadata, display=display)

    @classmethod
    def _resolve_context(
        cls, context: InputContractContext | InputEIP712Context, out: OutputAdder
    ) -> ResolvedContractContext | ResolvedEIP712Context | None:
        match context:
            case InputContractContext():
                return cls._resolve_context_contract(context, out)
            case InputEIP712Context():
                return cls._resolve_context_eip712(context, out)
            case _:
                assert_never(context)

    @classmethod
    def _resolve_metadata(cls, metadata: InputMetadata, out: OutputAdder) -> ResolvedMetadata | None:
        resolved_enums = {}
        if metadata.enums is not None:
            for enum_id, enum in metadata.enums.items():
                if (resolved_enum := cls._resolve_enum(enum, out)) is not None:
                    resolved_enums[enum_id] = resolved_enum

        return ResolvedMetadata(
            owner=metadata.owner,
            info=metadata.info,
            token=metadata.token,
            enums=resolved_enums,
        )

    @classmethod
    def _resolve_enum(cls, enum: HttpUrl | EnumDefinition, out: OutputAdder) -> dict[str, str] | None:
        match enum:
            case HttpUrl() as url:
                try:
                    return client.get(url=url, model=EnumDefinition)
                except Exception as e:
                    return out.error(
                        title="Failed to fetch enum definition from URL",
                        message=f'Failed to fetch enum definition from URL "{url}": {e}',
                    )
            case dict():
                return enum
            case _:
                assert_never(enum)

    @classmethod
    def _resolve_context_contract(
        cls, context: InputContractContext, out: OutputAdder
    ) -> ResolvedContractContext | None:
        if (contract := cls._resolve_contract(context.contract, out)) is None:
            return None

        return ResolvedContractContext(contract=contract)

    @classmethod
    def _resolve_contract(cls, contract: InputContract, out: OutputAdder) -> ResolvedContract | None:
        if (abi := cls._resolve_abis(contract.abi, out)) is None:
            return None

        return ResolvedContract(
            abi=abi, deployments=contract.deployments, addressMatcher=contract.addressMatcher, factory=contract.factory
        )

    @classmethod
    def _resolve_abis(cls, abis: list[ABI] | HttpUrl, out: OutputAdder) -> list[ABI] | None:
        match abis:
            case HttpUrl() as url:
                try:
                    return client.get(url=url, model=list[ABI])
                except Exception as e:
                    return out.error(
                        title="Failed to fetch ABI from URL",
                        message=f'Failed to fetch ABI from URL "{url}": {e}',
                    )
            case list():
                return abis
            case _:
                assert_never(abis)

    @classmethod
    def _resolve_context_eip712(cls, context: InputEIP712Context, out: OutputAdder) -> ResolvedEIP712Context | None:
        if (eip712 := cls._resolve_eip712(context.eip712, out)) is None:
            return None

        return ResolvedEIP712Context(eip712=eip712)

    @classmethod
    def _resolve_eip712(cls, eip712: InputEIP712, out: OutputAdder) -> ResolvedEIP712 | None:
        schemas = cls._resolve_schemas(eip712.schemas, out)

        if schemas is None:
            return None

        return ResolvedEIP712(
            domain=eip712.domain,
            schemas=schemas,
            domainSeparator=eip712.domainSeparator,
            deployments=eip712.deployments,
        )

    @classmethod
    def _resolve_schemas(
        cls, schemas: list[EIP712JsonSchema | HttpUrl], out: OutputAdder
    ) -> list[EIP712JsonSchema] | None:
        resolved_schemas = []
        for schema in schemas:
            if (resolved_schema := cls._resolve_schema(schema, out)) is not None:
                resolved_schemas.append(resolved_schema)
        return resolved_schemas

    @classmethod
    def _resolve_schema(cls, schema: EIP712JsonSchema | HttpUrl, out: OutputAdder) -> EIP712JsonSchema | None:
        match schema:
            case HttpUrl() as url:
                try:
                    return client.get(url=url, model=EIP712JsonSchema)
                except Exception as e:
                    return out.error(
                        title="Failed to fetch EIP-712 schema from URL",
                        message=f'Failed to fetch EIP-712 schema from URL "{url}": {e}',
                    )
            case EIP712JsonSchema():
                return schema
            case _:
                assert_never(schema)

    @classmethod
    def _resolve_display(
        cls,
        display: InputDisplay,
        context: ResolvedContractContext | ResolvedEIP712Context,
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
    ) -> ResolvedDisplay | None:
        formats = {}
        for format_id, format in display.formats.items():
            if (resolved_format_id := cls._resolve_format_id(format_id, context, out)) is None:
                return None
            if (
                resolved_format := cls._resolve_format(format, display.definitions or {}, enums, constants, out)
            ) is None:
                return None
            if resolved_format_id in formats:
                return out.error(
                    title="Duplicate format",
                    message=f"Descriptor contains 2 formats sections for {resolved_format_id}",
                )
            formats[resolved_format_id] = resolved_format

        return ResolvedDisplay(formats=formats)

    @classmethod
    def _resolve_field_description(
        cls,
        prefix: DataPath,
        definition: InputFieldDescription,
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
    ) -> ResolvedFieldDescription | None:
        match definition.format:
            case None | FieldFormat.RAW | FieldFormat.AMOUNT | FieldFormat.TOKEN_AMOUNT | FieldFormat.DURATION:
                pass
            case (
                FieldFormat.ADDRESS_NAME
                | FieldFormat.CALL_DATA
                | FieldFormat.NFT_NAME
                | FieldFormat.DATE
                | FieldFormat.UNIT
                | FieldFormat.ENUM
            ):
                if definition.params is None:
                    return out.error(
                        title="Missing parameters",
                        message=f"""Field format "{definition.format.value}" requires parameters to be defined, """
                        f"""they are missing for field "{definition.path}".""",
                    )
            case _:
                assert_never(definition.format)

        params = resolve_field_parameters(prefix, definition.params, enums, constants, out)

        if (path := constants.resolve_path(definition.path, out)) is None:
            return None

        return ResolvedFieldDescription.model_validate(
            {
                "$id": definition.id,
                "path": data_or_container_path_concat(prefix, path),
                "label": constants.resolve(definition.label, out),
                "format": FieldFormat(definition.format) if definition.format is not None else None,
                "params": params,
            }
        )

    @classmethod
    def _resolve_format_id(
        cls,
        format_id: str,
        context: ResolvedContractContext | ResolvedEIP712Context,
        out: OutputAdder,
    ) -> EIP712Type | Selector | None:
        match context:
            case ResolvedContractContext():
                if format_id.startswith("0x"):
                    return Selector(format_id)

                if (reduced_signature := reduce_signature(format_id)) is not None:
                    return Selector(signature_to_selector(reduced_signature))

                return out.error(
                    title="Invalid selector",
                    message=f""""{format_id}" is not a valid function signature or selector.""",
                )
            case ResolvedEIP712Context():
                return format_id
            case _:
                assert_never(context)

    @classmethod
    def _resolve_format(
        cls,
        format: InputFormat,
        definitions: dict[Id, InputFieldDefinition],
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
    ) -> ResolvedFormat | None:
        if (fields := cls._resolve_fields(ROOT_DATA_PATH, format.fields, definitions, enums, constants, out)) is None:
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
    def _resolve_fields(
        cls,
        prefix: DataPath,
        fields: list[InputField],
        definitions: dict[Id, InputFieldDefinition],
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
    ) -> list[ResolvedField] | None:
        resolved_fields = []
        for input_format in fields:
            if (resolved_field := cls._resolve_field(prefix, input_format, definitions, enums, constants, out)) is None:
                return None
            resolved_fields.append(resolved_field)
        return resolved_fields

    @classmethod
    def _resolve_field(
        cls,
        prefix: DataPath,
        field: InputField,
        definitions: dict[Id, InputFieldDefinition],
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
    ) -> ResolvedField | None:
        match field:
            case InputReference():
                return resolve_reference(prefix, field, definitions, enums, constants, out)
            case InputFieldDescription():
                return cls._resolve_field_description(prefix, field, enums, constants, out)
            case InputNestedFields():
                return cls._resolve_nested_fields(prefix, field, definitions, enums, constants, out)
            case _:
                assert_never(field)

    @classmethod
    def _resolve_nested_fields(
        cls,
        prefix: DataPath,
        fields: InputNestedFields,
        definitions: dict[Id, InputFieldDefinition],
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
    ) -> ResolvedNestedFields | None:
        path: DataPath
        match constants.resolve_path(fields.path, out):
            case None:
                return None
            case DataPath() as data_path:
                path = data_path_concat(prefix, data_path)
            case ContainerPath() as container_path:
                return out.error(
                    title="Invalid path type",
                    message=f"Container path {container_path} cannot be used with nested fields.",
                )
            case _:
                assert_never(fields.path)

        if (resolved_fields := cls._resolve_fields(path, fields.fields, definitions, enums, constants, out)) is None:
            return None

        return ResolvedNestedFields(path=path, fields=resolved_fields)
