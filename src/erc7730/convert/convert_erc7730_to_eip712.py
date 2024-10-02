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
from erc7730.model.context import Deployment, NameType
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

        if (domain := context.eip712.domain) is not None and domain.name is not None:
            name = domain.name
        elif descriptor.metadata.owner is not None:
            name = descriptor.metadata.owner
        else:
            return out.error("name is undefined")

        output_schema: dict[str, list[NameType]] = {}
        for schema in context.eip712.schemas:
            for type_, fields in schema.types.items():
                if (existing_fields := output_schema.get(type_)) is not None and fields != existing_fields:
                    return out.error(f"Descriptor schemas have colliding types (eg: {type_})")
                output_schema[type_] = fields

        messages: list[EIP712MessageDescriptor] = [
            EIP712MessageDescriptor.model_construct(
                schema=output_schema,
                mapper=EIP712Mapper.model_construct(
                    label=format_label,
                    fields=[out_field for in_field in format.fields for out_field in self.convert_field(in_field)],
                ),
            )
            for format_label, format in descriptor.display.formats.items()
        ]

        descriptors: dict[str, EIP712DAppDescriptor] = {}
        for deployment in context.eip712.deployments:
            if (output_descriptor := self._build_network_descriptor(deployment, name, messages, out)) is not None:
                descriptors[str(deployment.chainId)] = output_descriptor
        return descriptors

    @classmethod
    def _build_network_descriptor(
        cls,
        deployment: Deployment,
        name: str,
        messages: list[EIP712MessageDescriptor],
        out: OutputAdder,
    ) -> EIP712DAppDescriptor | None:
        if (network := ledger_network_id(deployment.chainId)) is None:
            return out.error(f"network id {deployment.chainId} not supported")

        return EIP712DAppDescriptor.model_construct(
            blockchainName=network,
            chainId=deployment.chainId,
            name=name,
            contracts=[
                EIP712ContractDescriptor.model_construct(
                    address=deployment.address.lower(), contractName=name, messages=messages
                )
            ],
        )

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
