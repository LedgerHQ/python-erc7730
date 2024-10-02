from typing import assert_never, final, override

from eip712 import (
    EIP712ContractDescriptor,
    EIP712DAppDescriptor,
    EIP712Field,
    EIP712Format,
    EIP712Mapper,
    EIP712MessageDescriptor,
)

from erc7730.common.ledger import ledger_network_id
from erc7730.common.output import OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.model.context import Deployment, EIP712JsonSchema, NameType
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
class ERC7730toEIP712Converter(ERC7730Converter[ResolvedERC7730Descriptor, EIP712DAppDescriptor]):
    """
    Converts ERC-7730 descriptor to Ledger legacy EIP-712 descriptor.

    Generates 1 output EIP712DAppDescriptor per chain id, as EIP-712 descriptors are chain-specific.
    """

    @override
    def convert(
        self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder
    ) -> dict[str, EIP712DAppDescriptor] | None:
        # note: model_construct() needs to be used here due to bad conception of EIP-712 library,
        # which adds computed fields on validation

        context = descriptor.context
        if not isinstance(context, ResolvedEIP712Context):
            return out.error("context is not EIP712")

        if (domain := context.eip712.domain) is None or (dapp_name := domain.name) is None:
            return out.error("EIP712 domain is not defined")

        if (contract_name := descriptor.metadata.owner) is None:
            return out.error("metadata.owner is not defined")

        messages: list[EIP712MessageDescriptor] = []
        for primary_type, format in descriptor.display.formats.items():
            schema = self._get_schema(primary_type, context.eip712.schemas, out)

            if schema is None:
                continue

            messages.append(
                EIP712MessageDescriptor.model_construct(
                    schema=schema,
                    mapper=EIP712Mapper.model_construct(
                        label=primary_type,
                        fields=[out_field for in_field in format.fields for out_field in self.convert_field(in_field)],
                    ),
                )
            )

        descriptors: dict[str, EIP712DAppDescriptor] = {}
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
        messages: list[EIP712MessageDescriptor],
        out: OutputAdder,
    ) -> EIP712DAppDescriptor | None:
        if (network := ledger_network_id(deployment.chainId)) is None:
            return out.error(f"network id {deployment.chainId} not supported")

        return EIP712DAppDescriptor.model_construct(
            blockchainName=network,
            chainId=deployment.chainId,
            name=dapp_name,
            contracts=[
                EIP712ContractDescriptor.model_construct(
                    address=deployment.address.lower(), contractName=contract_name, messages=messages
                )
            ],
        )

    @classmethod
    def _get_schema(
        cls, primary_type: str, schemas: list[EIP712JsonSchema], out: OutputAdder
    ) -> dict[str, list[NameType]] | None:
        for schema in schemas:
            if schema.primaryType == primary_type:
                return schema.types
        return out.error(f"schema for type {primary_type} not found")

    @classmethod
    def convert_field(cls, field: ResolvedField) -> list[EIP712Field]:
        if isinstance(field, ResolvedNestedFields):
            return [out_field for in_field in field.fields for out_field in cls.convert_field(in_field)]
        return [cls.convert_field_description(field)]

    @classmethod
    def convert_field_description(cls, field: ResolvedFieldDescription) -> EIP712Field:
        asset_path: str | None = None
        field_format: EIP712Format | None = None
        match field.format:
            case FieldFormat.TOKEN_AMOUNT:
                if field.params is not None and isinstance(field.params, TokenAmountParameters):
                    asset_path = field.params.tokenPath
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
        return EIP712Field(
            path=field.path,
            label=field.label,
            assetPath=asset_path,
            format=field_format,
        )
