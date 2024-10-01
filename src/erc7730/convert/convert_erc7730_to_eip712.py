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
    CallDataParameters,
    FieldFormat,
    NftNameParameters,
    TokenAmountParameters,
)
from erc7730.model.resolved.context import ResolvedEIP712Context
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.display import (
    ResolvedDisplay,
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
        # FIXME to debug and split in smaller methods

        context = descriptor.context
        if not isinstance(context, ResolvedEIP712Context):
            return error.error("context is None or is not EIP712")

        schemas = context.eip712.schemas

        messages = list[EIP712MessageDescriptor]()
        if context.eip712.domain is None:
            return error.error("domain is undefined")

        chain_id = context.eip712.domain.chainId
        if chain_id is None and context.eip712.deployments is not None:
            for deployment in context.eip712.deployments.root:
                chain_id = deployment.chainId
        contract_address = context.eip712.domain.verifyingContract
        if contract_address is None and context.eip712.deployments is not None:
            for deployment in context.eip712.deployments.root:
                contract_address = deployment.address
        if chain_id is None:
            return error.error("chain id is undefined")
        name = ""
        if context.eip712.domain.name is not None:
            name = context.eip712.domain.name
        if contract_address is None:
            return error.error("verifying contract is undefined")

        for format_label, format in descriptor.display.formats.items():
            eip712_fields = list[EIP712Field]()
            if format.fields is not None:
                for field in format.fields:
                    eip712_fields.extend(self.parse_field(descriptor.display, field))
            mapper = EIP712Mapper(label=format_label, fields=eip712_fields)
            messages.append(EIP712MessageDescriptor(schema=schemas[0].types, mapper=mapper))
        contracts = list[EIP712ContractDescriptor]()
        contract_name = name
        if descriptor.metadata.owner is not None:
            contract_name = descriptor.metadata.owner
        contracts.append(
            EIP712ContractDescriptor(address=contract_address, contractName=contract_name, messages=messages)
        )

        if (network := ledger_network_id(chain_id)) is None:
            return error.error(f"network id {chain_id} not supported")

        return EIP712DAppDescriptor(blockchainName=network, chainId=chain_id, name=name, contracts=contracts)

    @classmethod
    def parse_field(cls, display: ResolvedDisplay, field: ResolvedField) -> list[EIP712Field]:
        output = list[EIP712Field]()
        if isinstance(field, ResolvedNestedFields):
            for f in field.fields:
                output.extend(cls.parse_field(display, field=f))
        else:
            output.append(cls.convert_field(field))
        return output

    @classmethod
    def convert_field(cls, field: ResolvedFieldDescription) -> EIP712Field:
        name = field.label
        asset_path = None
        field_format = None
        match field.format:
            case FieldFormat.NFT_NAME:
                if field.params is not None and isinstance(field.params, NftNameParameters):
                    asset_path = field.params.collectionPath
            case FieldFormat.TOKEN_AMOUNT:
                if field.params is not None and isinstance(field.params, TokenAmountParameters):
                    asset_path = field.params.tokenPath
                field_format = EIP712Format.AMOUNT
            case FieldFormat.CALL_DATA:
                if field.params is not None and isinstance(field.params, CallDataParameters):
                    asset_path = field.params.calleePath
            case FieldFormat.AMOUNT:
                field_format = EIP712Format.AMOUNT
            case FieldFormat.DATE:
                field_format = EIP712Format.DATETIME
            case FieldFormat.RAW:
                field_format = EIP712Format.RAW
            case FieldFormat.ADDRESS_NAME:
                field_format = EIP712Format.RAW  # TODO not implemented
            case FieldFormat.DURATION:
                field_format = EIP712Format.RAW  # TODO not implemented
            case FieldFormat.ENUM:
                field_format = EIP712Format.RAW  # TODO not implemented
            case FieldFormat.UNIT:
                field_format = EIP712Format.RAW  # TODO not implemented
            case None:
                field_format = EIP712Format.RAW  # TODO not implemented
            case _:
                assert_never(field.format)
        return EIP712Field(path=field.path, label=name, assetPath=asset_path, format=field_format, coinRef=None)
