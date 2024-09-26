from pydantic import AnyUrl
from erc7730.common.pydantic import model_from_json_bytes
from erc7730.model.context import EIP712JsonSchema, EIP712Context, EIP712, Domain, NameType
from erc7730.model.erc7730_descriptor import ERC7730Descriptor
from erc7730.model.display import (
    CallDataParameters,
    Display,
    FieldDescription,
    NestedFields,
    NftNameParameters,
    Reference,
    FieldFormat,
    Field,
    Format,
    TokenAmountParameters,
)
from eip712 import (
    EIP712DAppDescriptor,
    EIP712ContractDescriptor,
    EIP712Mapper,
    EIP712MessageDescriptor,
    EIP712Field,
    EIP712Format,
)
import requests

from erc7730.model.metadata import Metadata


def to_eip712_mapper(erc7730: ERC7730Descriptor) -> EIP712DAppDescriptor | list[Exception]:
    exceptions = list[Exception]()
    context = erc7730.context
    if context is not None and isinstance(context, EIP712Context):
        erc7730schemasOrUrl = context.eip712.schemas
        eip712schema = dict[str, list[dict[str, str]]]()
        if erc7730schemasOrUrl is not None:
            for schemaOrUrl in erc7730schemasOrUrl:
                erc7730schema: EIP712JsonSchema | None = None
                if isinstance(schemaOrUrl, AnyUrl):
                    try:
                        response = requests.get(schemaOrUrl.__str__())
                        erc7730schema = model_from_json_bytes(response.content, model=EIP712JsonSchema)
                    except Exception as e:
                        exceptions.append(e)
                else:
                    erc7730schema = schemaOrUrl
                if erc7730schema is not None:
                    try:
                        eip712schema = erc7730schema.types
                    except Exception as e:
                        exceptions.append(e)

        if erc7730.display is not None:
            messages = list[EIP712MessageDescriptor]()
            if context.eip712.domain is not None:
                chainId = context.eip712.domain.chainId
                if chainId is None and context.eip712.deployments is not None:
                    for deployment in context.eip712.deployments.root:
                        if chainId is None and deployment.chainId is not None:
                            chainId = deployment.chainId
                contractAddress = context.eip712.domain.verifyingContract
                if contractAddress is None and context.eip712.deployments is not None:
                    for deployment in context.eip712.deployments.root:
                        if contractAddress is None and deployment.address is not None:
                            contractAddress = deployment.address
                if chainId is not None:
                    if chainId == 137:
                        blockchainName = "polygon"
                    else:
                        blockchainName = "ethereum"
                    name = ""
                    if context.eip712.domain.name is not None:
                        name = context.eip712.domain.name
                    if contractAddress is not None:
                        for lFormat in erc7730.display.formats:
                            format = erc7730.display.formats[lFormat]
                            eip712Fields = list[EIP712Field]()
                            if format.fields is not None:
                                for field in format.fields:
                                    eip712Fields.extend(parseField(erc7730.display, field))
                            mapper = EIP712Mapper(label=lFormat, fields=eip712Fields)
                            messages.append(EIP712MessageDescriptor(schema=eip712schema, mapper=mapper))
                        contracts = list[EIP712ContractDescriptor]()
                        contractName = name
                        if erc7730.metadata is not None and erc7730.metadata.owner is not None:
                            contractName = erc7730.metadata.owner
                        contracts.append(
                            EIP712ContractDescriptor(
                                address=contractAddress, contractName=contractName, messages=messages
                            )
                        )
                        return EIP712DAppDescriptor(
                            blockchainName=blockchainName, chainId=chainId, name=name, contracts=contracts
                        )
                    else:
                        exceptions.append(Exception(f"verifying contract is None for {context.eip712.domain}"))
                else:
                    exceptions.append(Exception(f"no chain id for {erc7730}"))
            else:
                exceptions.append(Exception(f"domain not defined for {erc7730}"))
        else:
            exceptions.append(Exception(f"no display for {erc7730}"))
    else:
        exceptions.append(Exception(f"context for {erc7730} is None or is not EIP712"))
    return exceptions


def parseField(display: Display, field: Field) -> list[EIP712Field]:
    output = list[EIP712Field]()
    fieldRoot = field.root
    if isinstance(fieldRoot, Reference):
        # get field from definition section
        if display.definitions is not None:
            f = display.definitions[fieldRoot.ref]
            output.append(parseFieldDescription(f))
    elif isinstance(fieldRoot, NestedFields):
        for f in fieldRoot.fields:  # type: ignore
            output.extend(parseField(display, field=f))  # type: ignore
    else:
        output.append(parseFieldDescription(fieldRoot))
    return output


def parseFieldDescription(field: FieldDescription) -> EIP712Field:
    name = field.label
    assetPath = None
    fieldFormat = None
    match field.format:
        case FieldFormat.NFT_NAME:
            if field.params is not None and isinstance(field.params, NftNameParameters):
                assetPath = field.params.collectionPath
        case FieldFormat.TOKEN_AMOUNT:
            if field.params is not None and isinstance(field.params, TokenAmountParameters):
                assetPath = field.params.tokenPath
            fieldFormat = EIP712Format.AMOUNT
        case FieldFormat.CALL_DATA:
            if field.params is not None and isinstance(field.params, CallDataParameters):
                assetPath = field.params.calleePath
        case FieldFormat.AMOUNT:
            fieldFormat = EIP712Format.AMOUNT
        case FieldFormat.DATE:
            fieldFormat = EIP712Format.DATETIME
        case FieldFormat.RAW:
            fieldFormat = EIP712Format.RAW
        case _:
            pass
    return EIP712Field(path=field.path, label=name, assetPath=assetPath, format=fieldFormat, coinRef=None)


def to_erc7730_mapper(eip712DappDescriptor: EIP712DAppDescriptor) -> ERC7730Descriptor:
    verifyingContract = None
    contractName = eip712DappDescriptor.name
    if eip712DappDescriptor.contracts.__len__() > 0:
        verifyingContract = eip712DappDescriptor.contracts[0].address
        contractName = eip712DappDescriptor.contracts[0].name
    domain = Domain(
        name=eip712DappDescriptor.name,
        version=None,
        chainId=eip712DappDescriptor.chain_id,
        verifyingContract=verifyingContract,
    )
    formats = dict[str, Format]()
    schemas = list[EIP712JsonSchema | AnyUrl]()
    for contract in eip712DappDescriptor.contracts:
        types = dict[str, list[NameType]]()
        for message in contract.messages:
            for primaryType in message.schema_:
                if isinstance(primaryType, str):
                    types[primaryType] = list[NameType]()
                    eip712Types = message.schema_[primaryType]
                    if isinstance(eip712Types, list):
                        for eip712Type in eip712Types:
                            if (
                                isinstance(eip712Type, dict)
                                and isinstance(eip712Type["name"], str)
                                and isinstance(eip712Type["type"], str)
                            ):
                                types[primaryType].append({"name": eip712Type["name"], "type": eip712Type["type"]})
            mapper = message.mapper
            fields = list[Field]()
            for item in mapper.fields:
                label = item.label
                path = item.path
                match item.format:
                    case EIP712Format.AMOUNT:
                        if item.assetPath is not None:
                            params = TokenAmountParameters(tokenPath=item.assetPath)
                            field = FieldDescription(
                                label=label, format=FieldFormat.TOKEN_AMOUNT, params=params, path=path
                            )
                        else:
                            field = FieldDescription(label=label, format=FieldFormat.AMOUNT, params=None, path=path)

                    case EIP712Format.DATETIME:
                        field = FieldDescription(label=label, format=FieldFormat.DATE, params=None, path=path)
                    case EIP712Format.RAW:
                        field = FieldDescription(label=label, format=FieldFormat.RAW, params=None, path=path)
                    case _:
                        field = FieldDescription(label=label, format=None, params=None, path=path)
                fields.append(Field(root=field))
            formats[mapper.label] = Format(
                intent=None,
                fields=fields,
                required=None,
                screens=None,
            )
            schemas.append(EIP712JsonSchema(primaryType=mapper.label, types=types))

    eip712 = EIP712(domain=domain, schemas=schemas)
    context = EIP712Context(eip712=eip712)
    display = Display(definitions=None, formats=formats)
    metadata = Metadata(owner=contractName, info=None, token=None, constants=None, enums=None)
    return ERC7730Descriptor(context=context, metadata=metadata, display=display)
