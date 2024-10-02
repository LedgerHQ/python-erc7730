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
from erc7730.convert import ERC7730Converter
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
    """Converts ERC-7730 descriptor to Ledger legacy EIP-712 descriptor."""

    @override
    def convert(
        self, descriptor: ResolvedERC7730Descriptor, error: ERC7730Converter.ErrorAdder
    ) -> EIP712DAppDescriptor | None:
        # note: model_construct() needs to be used here due to bad conception of EIP-712 library,
        # which adds computed fields on validation

        # FIXME to debug and split in smaller methods

        # FIXME this converter must be changed to output a list[EIP712DAppDescriptor]
        #  1 output EIP712DAppDescriptor per chain id

        context = descriptor.context
        if not isinstance(context, ResolvedEIP712Context):
            return error.error("context is not EIP712")

        schemas = context.eip712.schemas

        if (domain := context.eip712.domain) is None:
            return error.error("domain is undefined")

        chain_id = domain.chainId
        contract_address = domain.verifyingContract

        name = ""
        if domain.name is not None:
            name = domain.name

        for deployment in context.eip712.deployments:
            if chain_id is not None and contract_address is not None:
                break
            chain_id = deployment.chainId
            contract_address = deployment.address

        if chain_id is None:
            return error.error("chain id is undefined")
        if contract_address is None:
            return error.error("verifying contract is undefined")

        messages = [
            EIP712MessageDescriptor.model_construct(
                schema=schemas[0].types,  # FIXME
                mapper=EIP712Mapper.model_construct(
                    label=format_label,
                    fields=[out_field for in_field in format.fields for out_field in self.convert_field(in_field)],
                ),
            )
            for format_label, format in descriptor.display.formats.items()
        ]

        contract_name = name
        if descriptor.metadata.owner is not None:
            contract_name = descriptor.metadata.owner
        contracts = [
            EIP712ContractDescriptor.model_construct(
                address=contract_address.lower(), contractName=contract_name, messages=messages
            )
        ]

        if (network := ledger_network_id(chain_id)) is None:
            return error.error(f"network id {chain_id} not supported")

        return EIP712DAppDescriptor.model_construct(
            blockchainName=network, chainId=chain_id, name=name, contracts=contracts
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
