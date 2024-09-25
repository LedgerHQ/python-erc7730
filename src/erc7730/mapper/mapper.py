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
        domain = context.eip712.domain
        chain_id = None
        contract_address = None
        name = ""
        if domain is not None and domain.name is not None:
            name = domain.name
        if domain is not None and domain.chainId is not None:
            chain_id = domain.chainId
            contract_address = domain.verifyingContract
        if chain_id is None:
            if context.eip712.deployments is not None and context.eip712.deployments.root.__len__() > 0:
                chain_id = context.eip712.deployments.root[0].chainId
            else:
                exceptions.append(Exception(f"chain id is None for {domain}"))
        if contract_address is None:
            if domain is None or domain.verifyingContract is None:
                if context.eip712.deployments is not None and context.eip712.deployments.root.__len__() > 0:
                    contract_address = context.eip712.deployments.root[0].address
                else:
                    exceptions.append(Exception(f"verifying contract is None for {domain}"))
        schemas: dict[str, dict] = {}
        if (schs := context.eip712.schemas) is not None:
            for item in schs:
                sch = None
                if isinstance(item, EIP712JsonSchema):
                    sch = item
                else:
                    try:
                        response = requests.get(item.__str__())
                        sch = model_from_json_bytes(response.content, model=EIP712JsonSchema)
                    except Exception as e:
                        exceptions.append(e)
                if sch is not None:
                    schemas[sch.primaryType] = {}
                    for key, items in sch.types.items():
                        schemas[sch.primaryType][key] = items

        display = erc7730.display
        contracts = list[EIP712ContractDescriptor]()
        if display is not None:
            for key in display.formats:
                format = display.formats[key]
                messages = list[EIP712MessageDescriptor]()
                eip712Fields = list[EIP712Field]()
                if format.fields is not None:
                    for field in format.fields:
                        eip712Fields.extend(parseField(display, field))
                messages.append(
                    EIP712MessageDescriptor(schema=schemas[key], mapper=EIP712Mapper(label=key, fields=eip712Fields))
                )
                if contract_address is not None:
                    contracts.append(
                        EIP712ContractDescriptor(address=contract_address, contractName=name, messages=messages)
                    )
        if chain_id is not None:
            return EIP712DAppDescriptor(blockchainName="ethereum", chainId=chain_id, name=name, contracts=contracts)
        else:
            exceptions.append(Exception(f"no chain id for {erc7730}"))
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
    if eip712DappDescriptor.contracts.__len__() > 0:
        verifyingContract = eip712DappDescriptor.contracts[0].address
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
            mapper = message.mapper
            fields = list[Field]()
            types.update(message.schema_)
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
                    case _:
                        field = FieldDescription(label=label, format=FieldFormat.RAW, params=None, path=path)
                fields.append(Field(root=field))
            formats[mapper.label] = Format(
                id=None,
                intent=None,
                fields=fields,
                required=None,
                screens=None,  # type: ignore
            )
            schemas.append(EIP712JsonSchema(primaryType=mapper.label, types=types))

    eip712 = EIP712(domain=domain, schemas=schemas)
    context = EIP712Context(eip712=eip712)
    display = Display(definitions=None, formats=formats)
    metadata = Metadata(owner=None, info=None, token=None, constants=None, enums=None)
    return ERC7730Descriptor(context=context, metadata=metadata, display=display)
