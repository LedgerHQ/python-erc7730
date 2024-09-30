from typing import assert_never, final, override

import requests
from eip712 import (
    EIP712ContractDescriptor,
    EIP712DAppDescriptor,
    EIP712Field,
    EIP712Format,
    EIP712Mapper,
    EIP712MessageDescriptor,
)
from pydantic import AnyUrl

from erc7730.common.ledger import ledger_network_id
from erc7730.common.pydantic import model_from_json_bytes
from erc7730.convert import ERC7730Converter, FromERC7730Converter
from erc7730.model.context import EIP712Context, EIP712JsonSchema, NameType
from erc7730.model.descriptor import ERC7730Descriptor
from erc7730.model.display import (
    CallDataParameters,
    Display,
    Field,
    FieldDescription,
    FieldFormat,
    NestedFields,
    NftNameParameters,
    Reference,
    TokenAmountParameters,
)


@final
class ERC7730toEIP712Converter(FromERC7730Converter[EIP712DAppDescriptor]):
    """Converts ERC-7730 descriptor to Ledger legacy EIP-712 descriptor."""

    @override
    def convert(self, descriptor: ERC7730Descriptor, error: ERC7730Converter.ErrorAdder) -> EIP712DAppDescriptor | None:
        # FIXME to debug and split in smaller methods

        context = descriptor.context
        if context is None or not isinstance(context, EIP712Context):
            return error(
                ERC7730Converter.Error(
                    level=ERC7730Converter.Error.Level.FATAL, message="context is None or is not EIP712"
                )
            )

        eip712_schema = dict[str, list[NameType]]()
        if (erc7730_schemas_or_url := context.eip712.schemas) is not None:
            for schema_or_url in erc7730_schemas_or_url:
                erc7730_schema: EIP712JsonSchema | None = None
                if isinstance(schema_or_url, AnyUrl):
                    try:
                        response = requests.get(str(schema_or_url), timeout=10)
                        erc7730_schema = model_from_json_bytes(response.content, model=EIP712JsonSchema)
                    except Exception as e:
                        return error(ERC7730Converter.Error(level=ERC7730Converter.Error.Level.FATAL, message=str(e)))
                else:
                    erc7730_schema = schema_or_url
                if erc7730_schema is not None:
                    try:
                        eip712_schema = erc7730_schema.types
                    except Exception as e:
                        return error(ERC7730Converter.Error(level=ERC7730Converter.Error.Level.FATAL, message=str(e)))
        if descriptor.display is None:
            return error(
                ERC7730Converter.Error(level=ERC7730Converter.Error.Level.FATAL, message="display is undefined")
            )

        messages = list[EIP712MessageDescriptor]()
        if context.eip712.domain is None:
            return error(
                ERC7730Converter.Error(level=ERC7730Converter.Error.Level.FATAL, message="domain is undefined")
            )

        chain_id = context.eip712.domain.chainId
        if chain_id is None and context.eip712.deployments is not None:
            for deployment in context.eip712.deployments.root:
                if chain_id is None and deployment.chainId is not None:
                    chain_id = deployment.chainId
        contract_address = context.eip712.domain.verifyingContract
        if contract_address is None and context.eip712.deployments is not None:
            for deployment in context.eip712.deployments.root:
                if contract_address is None and deployment.address is not None:
                    contract_address = deployment.address
        if chain_id is None:
            return error(
                ERC7730Converter.Error(level=ERC7730Converter.Error.Level.FATAL, message="chain id is undefined")
            )
        name = ""
        if context.eip712.domain.name is not None:
            name = context.eip712.domain.name
        if contract_address is None:
            return error(
                ERC7730Converter.Error(
                    level=ERC7730Converter.Error.Level.FATAL, message="verifying contract is undefined"
                )
            )

        for format_label, format in descriptor.display.formats.items():
            eip712_fields = list[EIP712Field]()
            if format.fields is not None:
                for field in format.fields:
                    eip712_fields.extend(self.parse_field(descriptor.display, field))
            mapper = EIP712Mapper(label=format_label, fields=eip712_fields)
            messages.append(EIP712MessageDescriptor(schema=eip712_schema, mapper=mapper))
        contracts = list[EIP712ContractDescriptor]()
        contract_name = name
        if descriptor.metadata is not None and descriptor.metadata.owner is not None:
            contract_name = descriptor.metadata.owner
        contracts.append(
            EIP712ContractDescriptor(address=contract_address, contractName=contract_name, messages=messages)
        )

        if (network := ledger_network_id(chain_id)) is None:
            return error(
                ERC7730Converter.Error(
                    level=ERC7730Converter.Error.Level.FATAL, message=f"network id {chain_id} not supported"
                )
            )

        return EIP712DAppDescriptor(blockchainName=network, chainId=chain_id, name=name, contracts=contracts)

    @classmethod
    def parse_field(cls, display: Display, field: Field) -> list[EIP712Field]:
        output = list[EIP712Field]()
        field_root = field.root
        if isinstance(field_root, Reference):
            # get field from definition section
            if display.definitions is not None:
                f = display.definitions[field_root.ref]
                output.append(cls.convert_field(f))
        elif isinstance(field_root, NestedFields):
            for f in field_root.fields:  # type: ignore
                output.extend(cls.parse_field(display, field=f))  # type: ignore
        else:
            output.append(cls.convert_field(field_root))
        return output

    @classmethod
    def convert_field(cls, field: FieldDescription) -> EIP712Field:
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
