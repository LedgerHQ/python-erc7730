from typing import assert_never, final, override

from eip712.model.input.contract import InputEIP712Contract
from eip712.model.input.descriptor import InputEIP712DAppDescriptor
from eip712.model.input.message import InputEIP712Mapper, InputEIP712MapperField, InputEIP712Message
from eip712.model.schema import EIP712SchemaField
from eip712.model.types import EIP712Format, EIP712NameSource, EIP712NameType

from erc7730.common.ledger import ledger_network_id
from erc7730.common.output import ExceptionsToOutput, OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.model.context import EIP712Schema
from erc7730.model.display import AddressNameType, FieldFormat
from erc7730.model.paths import ContainerField, ContainerPath, DataPath
from erc7730.model.paths.path_ops import data_path_concat, to_relative
from erc7730.model.resolved.context import ResolvedDeployment, ResolvedEIP712Context
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.display import (
    ResolvedAddressNameParameters,
    ResolvedCallDataParameters,
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedNestedFields,
    ResolvedTokenAmountParameters,
    ResolvedValue,
    ResolvedValueConstant,
    ResolvedValuePath,
)

# EIP-712 canonical domain field order and types as specified in the EIP-712 standard.
# See https://eips.ethereum.org/EIPS/eip-712#definition-of-domainseparator
EIP712_DOMAIN_CANONICAL_ORDER: list[tuple[str, str]] = [
    ("name", "string"),
    ("version", "string"),
    ("chainId", "uint256"),
    ("verifyingContract", "address"),
    ("salt", "bytes32"),
]

_EIP712_DOMAIN_KNOWN_NAMES = {name for name, _ in EIP712_DOMAIN_CANONICAL_ORDER}


def validate_eip712_domain_fields(
    domain_fields: list[EIP712SchemaField],
    out: OutputAdder,
) -> None:
    """Validate the EIP712Domain type fields against the canonical EIP-712 order.

    Emits warnings for:
    * Fields not in the canonical list (name, version, chainId, verifyingContract, salt).
    * Fields that are out of the EIP-712 canonical order.

    :param domain_fields: the EIP712Domain fields from the schema
    :param out: warning handler
    """
    canonical_order = [name for name, _ in EIP712_DOMAIN_CANONICAL_ORDER]

    # Check for unknown fields
    for field in domain_fields:
        if field.name not in _EIP712_DOMAIN_KNOWN_NAMES:
            out.warning(
                title="Non-standard EIP712Domain field",
                message=f'EIP712Domain field "{field.name}" is not part of the EIP-712 standard '
                f"(expected: {', '.join(canonical_order)}).",  # no brackets — rich interprets them as tags
            )

    # Check ordering: filter to only known fields and verify they appear in canonical order
    known_field_names = [f.name for f in domain_fields if f.name in _EIP712_DOMAIN_KNOWN_NAMES]
    canonical_positions = {name: i for i, name in enumerate(canonical_order)}
    expected_order = sorted(known_field_names, key=lambda n: canonical_positions[n])

    if known_field_names != expected_order:
        out.warning(
            title="EIP712Domain field order",
            message=f"EIP712Domain fields are not in the canonical EIP-712 order. "
            f"Found: ({', '.join(known_field_names)}), "
            f"expected: ({', '.join(expected_order)}).",
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
        with ExceptionsToOutput(out):
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

                output_fields = []
                for input_field in format.fields:
                    if (out_field := self.convert_field(input_field, None, out)) is None:
                        return None
                    output_fields.extend(out_field)

                messages.append(
                    InputEIP712Message(schema=schema, mapper=InputEIP712Mapper(label=label, fields=output_fields))
                )

            descriptors: dict[str, InputEIP712DAppDescriptor] = {}
            for deployment in context.eip712.deployments:
                chain_id = str(deployment.chainId)
                output_descriptor = self._build_network_descriptor(
                    deployment, dapp_name, contract_name, messages, descriptors.get(chain_id), out
                )
                if output_descriptor is not None:
                    descriptors[chain_id] = output_descriptor

        return descriptors

    @classmethod
    def _build_network_descriptor(
        cls,
        deployment: ResolvedDeployment,
        dapp_name: str,
        contract_name: str,
        messages: list[InputEIP712Message],
        descriptor: InputEIP712DAppDescriptor | None,
        out: OutputAdder,
    ) -> InputEIP712DAppDescriptor | None:
        if (network := ledger_network_id(deployment.chainId)) is None:
            out.error(f"network id {deployment.chainId} not supported")
            return descriptor

        contracts = descriptor.contracts if descriptor is not None else []

        contracts.append(
            InputEIP712Contract(address=deployment.address.lower(), contractName=contract_name, messages=messages)
        )

        return InputEIP712DAppDescriptor(
            blockchainName=network,
            chainId=deployment.chainId,
            name=dapp_name,
            contracts=contracts,
        )

    @classmethod
    def _get_schema(
        cls, primary_type: str, schemas: list[EIP712Schema], out: OutputAdder
    ) -> dict[str, list[EIP712SchemaField]] | None:
        for schema in schemas:
            if schema.primaryType == primary_type:
                # Validate EIP712Domain field ordering and names
                if "EIP712Domain" in schema.types:
                    validate_eip712_domain_fields(schema.types["EIP712Domain"], out)
                return schema.types
        return out.error(f"schema for type {primary_type} not found")

    @classmethod
    def convert_field(
        cls, field: ResolvedField, prefix: DataPath | None, out: OutputAdder
    ) -> list[InputEIP712MapperField] | None:
        match field:
            case ResolvedFieldDescription():
                if (output_field := cls.convert_field_description(field, prefix, out)) is None:
                    return None
                return [output_field]
            case ResolvedNestedFields():
                output_fields = []
                for in_field in field.fields:
                    if (output_field := cls.convert_field(in_field, prefix, out)) is None:
                        return None
                    output_fields.extend(output_field)
                return output_fields
            case _:
                assert_never(field)

    @classmethod
    def convert_field_description(
        cls,
        field: ResolvedFieldDescription,
        prefix: DataPath | None,
        out: OutputAdder,
    ) -> InputEIP712MapperField | None:
        field_path: DataPath
        asset_path: DataPath | None = None
        field_format: EIP712Format | None = None

        match field.value:
            case ResolvedValueConstant():
                return out.error("Constant values are not supported")

            case ResolvedValuePath(path=path):
                match path:
                    case DataPath() as field_path:
                        field_path = data_path_concat(prefix, field_path)
                    case ContainerPath() as container_path:
                        return out.error(f"Path {container_path} is not supported")
                    case _:
                        assert_never(field.value)
            case _:
                assert_never(field.value)

        match field.format:
            case None:
                field_format = None
            case FieldFormat.ADDRESS_NAME:
                field_format = EIP712Format.TRUSTED_NAME
            case FieldFormat.RAW:
                field_format = EIP712Format.RAW
            case FieldFormat.ENUM:
                field_format = EIP712Format.RAW
            case FieldFormat.UNIT:
                field_format = EIP712Format.RAW
            case FieldFormat.DURATION:
                field_format = EIP712Format.RAW
            case FieldFormat.NFT_NAME:
                field_format = EIP712Format.TRUSTED_NAME
            case FieldFormat.CALL_DATA:
                field_format = EIP712Format.CALLDATA
            case FieldFormat.DATE:
                field_format = EIP712Format.DATETIME
            case FieldFormat.AMOUNT:
                field_format = EIP712Format.AMOUNT
            case FieldFormat.TOKEN_AMOUNT:
                field_format = EIP712Format.AMOUNT
                if field.params is not None and isinstance(field.params, ResolvedTokenAmountParameters):
                    match field.params.token:
                        case None:
                            return out.error("Token path or reference must be set")

                        case ResolvedValueConstant():
                            return out.error("Constant values are not supported")

                        case ResolvedValuePath(path=path):
                            match path:
                                case None:
                                    pass
                                case DataPath() as token_path:
                                    asset_path = data_path_concat(prefix, token_path)
                                case ContainerPath() as container_path if container_path.field == ContainerField.TO:
                                    # In EIP-712 protocol, format=token with no token path
                                    #  => refers to verifyingContract
                                    asset_path = None
                                case ContainerPath() as container_path:
                                    return out.error(f"Path {container_path} is not supported")
                                case _:
                                    assert_never(path)
                        case _:
                            assert_never(field.value)
            case _:
                assert_never(field.format)

        # Trusted names
        name_types: list[EIP712NameType] | None = None
        name_sources: list[EIP712NameSource] | None = None

        if (
            field_format == EIP712Format.TRUSTED_NAME
            and field.params is not None
            and isinstance(field.params, ResolvedAddressNameParameters)
        ):
            name_types = cls.convert_trusted_names_types(field.params.types)
            name_sources = cls.convert_trusted_names_sources(field.params.sources, name_types)

        # Calldata
        callee_path: str | None = None
        chainid_path: str | None = None
        selector_path: str | None = None
        amount_path: str | None = None
        spender_path: str | None = None

        if (
            (field_format == EIP712Format.CALLDATA)
            and field.params is not None
            and isinstance(field.params, ResolvedCallDataParameters)
        ):
            try:
                callee_path = cls.convert_calldata_param_path(prefix, field.params.callee)
                chainid_path = cls.convert_calldata_param_path(prefix, field.params.chainId)
                selector_path = cls.convert_calldata_param_path(prefix, field.params.selector)
                amount_path = cls.convert_calldata_param_path(prefix, field.params.amount)
                spender_path = cls.convert_calldata_param_path(prefix, field.params.spender)
            except ValueError as e:
                return out.error(str(e))

        return InputEIP712MapperField(
            path=str(to_relative(field_path)),
            label=field.label,
            assetPath=None if asset_path is None else str(to_relative(asset_path)),
            format=field_format,
            nameTypes=name_types,
            nameSources=name_sources,
            calleePath=callee_path,
            chainIdPath=chainid_path,
            selectorPath=selector_path,
            amountPath=amount_path,
            spenderPath=spender_path,
        )

    @classmethod
    def convert_trusted_names_types(cls, types: list[AddressNameType] | None) -> list[EIP712NameType] | None:
        if types is None:
            return None

        name_types: list[EIP712NameType] = []
        for name_type in types:
            match name_type:
                case AddressNameType.WALLET:
                    name_types.append(EIP712NameType.WALLET)
                case AddressNameType.EOA:
                    name_types.append(EIP712NameType.EOA)
                case AddressNameType.CONTRACT:
                    name_types.append(EIP712NameType.SMART_CONTRACT)
                case AddressNameType.TOKEN:
                    name_types.append(EIP712NameType.TOKEN)
                case AddressNameType.COLLECTION:
                    name_types.append(EIP712NameType.COLLECTION)
                case _:
                    assert_never(name_type)

        return name_types

    @classmethod
    def convert_trusted_names_sources(
        cls, sources: list[str] | None, names: list[EIP712NameType] | None
    ) -> list[EIP712NameSource] | None:
        if sources is None:
            return None
        name_sources: list[EIP712NameSource] = []

        if names is not None:
            for name in names:
                match name:
                    case EIP712NameType.EOA | EIP712NameType.WALLET | EIP712NameType.COLLECTION:
                        name_sources.append(EIP712NameSource.ENS)
                        name_sources.append(EIP712NameSource.UNSTOPPABLE_DOMAIN)
                        name_sources.append(EIP712NameSource.FREENAME)
                    case EIP712NameType.SMART_CONTRACT | EIP712NameType.TOKEN:
                        name_sources.append(EIP712NameSource.CRYPTO_ASSET_LIST)
                    case EIP712NameType.CONTEXT_ADDRESS:
                        name_sources.append(EIP712NameSource.DYNAMIC_RESOLVER)
                    case _:
                        assert_never(name)

        for name_source in sources:
            if name_source == "local":  # ERC-7730 specs defines "local" as an example
                name_sources.append(EIP712NameSource.LOCAL_ADDRESS_BOOK)
            elif name_source in set(EIP712NameSource) and name_source not in name_sources:
                name_sources.append(EIP712NameSource(name_source))
            # else: ignore

        if not name_sources:  # default to all sources
            name_sources = list(EIP712NameSource)
        return name_sources

    @classmethod
    def convert_calldata_param_path(cls, prefix: DataPath | None, input_path: ResolvedValue | None) -> str | None:
        match input_path:
            case None:
                return None

            case ResolvedValueConstant():
                raise ValueError("Constant values are not supported")

            case ResolvedValuePath(path=path):
                match path:
                    case DataPath() as token_path:
                        return str(to_relative(data_path_concat(prefix, token_path)))
                    case ContainerPath() as container_path if container_path.field == ContainerField.TO:
                        return "@.to"
                    case ContainerPath() as container_path:
                        raise ValueError(f"Path {container_path} is not supported")
                    case _:
                        assert_never(path)
            case _:
                assert_never(input_path)
