from typing import assert_never, final, override

from eip712.model.input.contract import InputEIP712Contract
from eip712.model.input.descriptor import InputEIP712DAppDescriptor
from eip712.model.input.message import InputEIP712Mapper, InputEIP712MapperField, InputEIP712Message
from eip712.model.schema import EIP712SchemaField
from eip712.model.types import EIP712Format

from erc7730.common.ledger import ledger_network_id
from erc7730.common.output import OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.model.context import Deployment, EIP712JsonSchema
from erc7730.model.display import (
    FieldFormat,
    TokenAmountParameters,
)
from erc7730.model.resolved.context import ResolvedEIP712Context
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.display import (
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedNestedFields,
)


@final
class ERC7730toEIP712Converter(ERC7730Converter[ResolvedERC7730Descriptor, InputEIP712DAppDescriptor]):
    """
    Converts ERC-7730 descriptor to Ledger legacy EIP-712 descriptor.

    Generates 1 output InputEIP712DAppDescriptor per chain id, as EIP-712 descriptors are chain-specific.
    """

    @override
    def convert(
        self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder
    ) -> dict[str, InputEIP712DAppDescriptor] | None:
        context = descriptor.context
        if not isinstance(context, ResolvedEIP712Context):
            return out.error("context is not EIP712")

        if (domain := context.eip712.domain) is None or (dapp_name := domain.name) is None:
            return out.error("EIP712 domain is not defined")

        if (contract_name := descriptor.metadata.owner) is None:
            return out.error("metadata.owner is not defined")

        messages: list[InputEIP712Message] = []
        for primary_type, format in descriptor.display.formats.items():
            schema = self._get_schema(primary_type, context.eip712.schemas, out)

            if schema is None:
                return out.error(f"EIP-712 schema for {primary_type} is missing")

            label = format.intent if isinstance(format.intent, str) else primary_type

            messages.append(
                InputEIP712Message.model_construct(
                    schema=schema,
                    mapper=InputEIP712Mapper.model_construct(
                        label=label,
                        fields=[
                            out_field
                            for in_field in format.fields
                            for out_field in self.convert_field(in_field, prefix=None)
                        ],
                    ),
                )
            )

        descriptors: dict[str, InputEIP712DAppDescriptor] = {}
        for deployment in context.eip712.deployments:
            output_descriptor = self._build_network_descriptor(deployment, dapp_name, contract_name, messages, out)
            if output_descriptor is not None:
                descriptors[str(deployment.chainId)] = output_descriptor
        return descriptors

    @classmethod
    def _build_network_descriptor(
        cls,
        deployment: Deployment,
        dapp_name: str,
        contract_name: str,
        messages: list[InputEIP712Message],
        out: OutputAdder,
    ) -> InputEIP712DAppDescriptor | None:
        if (network := ledger_network_id(deployment.chainId)) is None:
            return out.error(f"network id {deployment.chainId} not supported")

        return InputEIP712DAppDescriptor.model_construct(
            blockchainName=network,
            chainId=deployment.chainId,
            name=dapp_name,
            contracts=[
                InputEIP712Contract.model_construct(
                    address=deployment.address.lower(), contractName=contract_name, messages=messages
                )
            ],
        )

    @classmethod
    def _get_schema(
        cls, primary_type: str, schemas: list[EIP712JsonSchema], out: OutputAdder
    ) -> dict[str, list[EIP712SchemaField]] | None:
        for schema in schemas:
            if schema.primaryType == primary_type:
                return schema.types
        return out.error(f"schema for type {primary_type} not found")

    @classmethod
    def convert_field(cls, field: ResolvedField, prefix: str | None) -> list[InputEIP712MapperField]:
        if isinstance(field, ResolvedNestedFields):
            field_prefix = field.path if prefix is None else f"{prefix}.{field.path}"
            return [out_field for in_field in field.fields for out_field in cls.convert_field(in_field, field_prefix)]
        return [cls.convert_field_description(field, prefix)]

    @classmethod
    def convert_field_description(cls, field: ResolvedFieldDescription, prefix: str | None) -> InputEIP712MapperField:
        asset_path: str | None = None
        field_format: EIP712Format | None = None
        match field.format:
            case FieldFormat.TOKEN_AMOUNT:
                if field.params is not None and isinstance(field.params, TokenAmountParameters):
                    asset_path = field.params.tokenPath if prefix is None else f"{prefix}.{field.params.tokenPath}"

                    # FIXME edge case for referencing verifyingContract, this will be handled cleanly in #65
                    if asset_path == "@.to":
                        asset_path = None

                field_format = EIP712Format.AMOUNT
            case FieldFormat.AMOUNT:
                field_format = EIP712Format.AMOUNT
            case FieldFormat.DATE:
                field_format = EIP712Format.DATETIME
            case FieldFormat.ADDRESS_NAME:
                field_format = EIP712Format.RAW
            case FieldFormat.ENUM:
                field_format = EIP712Format.RAW
            case FieldFormat.UNIT:
                field_format = EIP712Format.RAW
            case FieldFormat.DURATION:
                field_format = EIP712Format.RAW
            case FieldFormat.NFT_NAME:
                field_format = EIP712Format.RAW
            case FieldFormat.CALL_DATA:
                field_format = EIP712Format.RAW
            case FieldFormat.RAW:
                field_format = EIP712Format.RAW
            case None:
                field_format = None
            case _:
                assert_never(field.format)
        return InputEIP712MapperField(
            path=field.path if prefix is None else f"{prefix}.{field.path}",
            label=field.label,
            assetPath=asset_path,
            format=field_format,
        )
