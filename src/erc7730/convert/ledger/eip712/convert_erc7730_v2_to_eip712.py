"""
Conversion of v2 ERC-7730 input descriptors to Ledger legacy EIP-712 descriptors.

In v2, the EIP-712 schemas are no longer embedded in ``context.eip712.schemas``.  Instead, the
``display.formats`` keys are **encodeType** strings (e.g.
``Order(address owner,Bridge bridge)Bridge(bytes4 sel,uint256 chainId)``) from which the full
EIP-712 schema can be reconstructed.

This module provides:

* ``parse_encode_type`` (from ``common.abi``): reverses an encodeType string into
  ``(primaryType, types_dict)``
* ``_reconstruct_eip712_domain``: rebuilds the ``EIP712Domain`` type from the v2 resolved domain
  and deployment information
* ``ERC7730V2toEIP712Converter``: the converter class that ties everything together
"""

from typing import final

from eip712.model.input.contract import InputEIP712Contract
from eip712.model.input.descriptor import InputEIP712DAppDescriptor
from eip712.model.input.message import InputEIP712Mapper, InputEIP712MapperField, InputEIP712Message
from eip712.model.schema import EIP712SchemaField
from eip712.model.types import EIP712Format, EIP712NameSource, EIP712NameType

from erc7730.common.abi import parse_encode_type
from erc7730.common.ledger import ledger_network_id
from erc7730.common.output import ConsoleOutputAdder, ExceptionsToOutput, OutputAdder
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.display import AddressNameType
from erc7730.model.input.v2.context import InputEIP712Context
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.input.v2.format import FieldFormat
from erc7730.model.paths import ContainerPath, DataPath
from erc7730.model.paths.path_ops import to_relative
from erc7730.model.paths.path_parser import to_path
from erc7730.model.resolved.v2.context import ResolvedDeployment, ResolvedDomain, ResolvedEIP712Context
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.v2.display import (
    ResolvedAddressNameParameters,
    ResolvedCallDataParameters,
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFieldGroup,
    ResolvedTokenAmountParameters,
)


# ---------------------------------------------------------------------------
# Domain reconstruction
# ---------------------------------------------------------------------------


def _reconstruct_eip712_domain(
    domain: ResolvedDomain | None,
    has_deployments: bool,
    out: OutputAdder,
) -> list[EIP712SchemaField]:
    """Reconstruct the ``EIP712Domain`` type fields from v2 resolved domain info.

    Fields are emitted in the canonical EIP-712 order:
    ``name``, ``version``, ``chainId``, ``verifyingContract``, ``salt``.

    Rules (as specified):
    * Always add ``name`` (string) and ``version`` (string); warn if absent in domain.
    * If deployments exist, always add ``chainId`` (uint256) and ``verifyingContract`` (address).

    :param domain: the resolved domain, or ``None``
    :param has_deployments: whether the descriptor has a ``deployments`` array
    :param out: error / warning handler
    :return: list of ``EIP712SchemaField`` for the ``EIP712Domain`` type, in canonical order
    """
    fields: list[EIP712SchemaField] = []

    # 1. name (always present)
    if domain is None or domain.name is None:
        out.warning(
            title="Missing domain name",
            message="EIP-712 domain 'name' is not set in the descriptor; adding to schema with type 'string' anyway.",
        )
    fields.append(EIP712SchemaField(name="name", type="string"))

    # 2. version (always present)
    if domain is None or domain.version is None:
        out.warning(
            title="Missing domain version",
            message="EIP-712 domain 'version' is not set in the descriptor; adding to schema with type 'string' anyway.",
        )
    fields.append(EIP712SchemaField(name="version", type="string"))

    # 3. chainId + 4. verifyingContract (only if deployments are present)
    if has_deployments:
        fields.append(EIP712SchemaField(name="chainId", type="uint256"))
        fields.append(EIP712SchemaField(name="verifyingContract", type="address"))

    return fields


# ---------------------------------------------------------------------------
# Schema reconstruction from encodeType strings
# ---------------------------------------------------------------------------


def _build_schema(
    encode_type_key: str,
    domain_fields: list[EIP712SchemaField],
    out: OutputAdder,
) -> tuple[str, dict[str, list[EIP712SchemaField]]] | None:
    """Build an EIP-712 schema (types dict) from an encodeType format key.

    :param encode_type_key: an encodeType string from ``display.formats``
    :param domain_fields: pre-built ``EIP712Domain`` type fields
    :param out: error handler
    :return: (primaryType, types dict) or ``None`` on error
    """
    try:
        primary_type, raw_types = parse_encode_type(encode_type_key)
    except ValueError as e:
        out.error(
            title="Invalid encodeType",
            message=f"Failed to parse format key as encodeType: {e}",
        )
        return None

    types: dict[str, list[EIP712SchemaField]] = {}

    # Add EIP712Domain
    types["EIP712Domain"] = domain_fields

    # Add parsed types
    for type_name, field_tuples in raw_types.items():
        types[type_name] = [EIP712SchemaField(name=name, type=typ) for typ, name in field_tuples]

    return primary_type, types


# ---------------------------------------------------------------------------
# V2 field conversion helpers
# ---------------------------------------------------------------------------


def _resolve_path_string(path_str: str) -> str:
    """Convert a v2 resolved path string to a relative path string suitable for the legacy EIP-712 format.

    :param path_str: v2 path string (e.g. ``#.amount``, ``@.from``)
    :return: relative path string (e.g. ``amount``, ``@.from``)
    """
    parsed = to_path(path_str)
    match parsed:
        case DataPath():
            return str(to_relative(parsed))
        case ContainerPath():
            return str(parsed)
        case _:
            return path_str


def _convert_v2_field(
    field: ResolvedField,
    out: OutputAdder,
) -> list[InputEIP712MapperField] | None:
    """Convert a v2 resolved field to legacy EIP-712 mapper field(s).

    :param field: a v2 resolved field
    :param out: error handler
    :return: list of mapper fields, or ``None`` on error
    """
    if isinstance(field, ResolvedFieldDescription):
        # Skip hidden fields (equivalent of v1 "excluded")
        if field.visible == "never":
            return []

        if (output_field := _convert_v2_field_description(field, out)) is None:
            return None
        return [output_field]

    elif isinstance(field, ResolvedFieldGroup):
        output_fields: list[InputEIP712MapperField] = []
        for nested_field in field.fields:
            if (nested_output := _convert_v2_field(nested_field, out)) is None:
                return None
            output_fields.extend(nested_output)
        return output_fields

    else:
        return out.error(
            title="Unknown field type",
            message=f"Unexpected resolved field type: {type(field)}",
        )


def _convert_v2_field_description(
    field: ResolvedFieldDescription,
    out: OutputAdder,
) -> InputEIP712MapperField | None:
    """Convert a single v2 resolved field description to a legacy EIP-712 mapper field.

    This adapts the v1 ``ERC7730toEIP712Converter.convert_field_description`` to work with v2
    resolved models where paths are strings and parameters use v2 model types.
    """

    # --- Path extraction ---
    if field.value is not None:
        return out.error(
            title="Constant values not supported",
            message="Constant values cannot be converted to legacy EIP-712 fields.",
        )

    if field.path is None:
        return out.error(
            title="Missing path",
            message="Field has neither path nor value.",
        )

    field_path_str = str(field.path)

    # Check that the path is a data path (not a container path)
    parsed_path = to_path(field_path_str)
    if isinstance(parsed_path, ContainerPath):
        return out.error(
            title="Unsupported path",
            message=f'Container path "{field_path_str}" is not supported in EIP-712 conversion.',
        )
    if not isinstance(parsed_path, DataPath):
        return out.error(
            title="Unsupported path type",
            message=f'Path "{field_path_str}" is not a data path.',
        )

    relative_path = str(to_relative(parsed_path))

    # --- Format mapping ---
    asset_path: str | None = None
    field_format: EIP712Format | None = None

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
                if field.params.tokenPath is not None:
                    token_path_str = str(field.params.tokenPath)
                    token_parsed = to_path(token_path_str)
                    if isinstance(token_parsed, ContainerPath) and str(token_parsed) == "@.to":
                        # In EIP-712 protocol, format=token with no token path => refers to verifyingContract
                        asset_path = None
                    elif isinstance(token_parsed, DataPath):
                        asset_path = str(to_relative(token_parsed))
                    else:
                        return out.error(
                            title="Unsupported token path",
                            message=f'Token path "{token_path_str}" is not supported.',
                        )
                elif field.params.token is not None:
                    # token is a resolved constant address -- cannot be represented in legacy format
                    return out.error(
                        title="Constant token not supported",
                        message="Constant token addresses cannot be converted to legacy EIP-712 fields.",
                    )
                else:
                    return out.error(
                        title="Missing token",
                        message="Token path or reference must be set for tokenAmount format.",
                    )
        case FieldFormat.INTEROPERABLE_ADDRESS_NAME:
            field_format = EIP712Format.TRUSTED_NAME
        case FieldFormat.TOKEN_TICKER:
            field_format = EIP712Format.RAW
        case FieldFormat.CHAIN_ID:
            field_format = EIP712Format.RAW
        case _:
            return out.error(
                title="Unsupported format",
                message=f'Field format "{field.format}" is not supported for EIP-712 conversion.',
            )

    # --- Trusted names ---
    name_types: list[EIP712NameType] | None = None
    name_sources: list[EIP712NameSource] | None = None

    if (
        field_format == EIP712Format.TRUSTED_NAME
        and field.params is not None
        and isinstance(field.params, ResolvedAddressNameParameters)
    ):
        name_types = _convert_trusted_names_types(field.params.types)
        name_sources = _convert_trusted_names_sources(field.params.sources, name_types)

    # --- Calldata params ---
    callee_path: str | None = None
    chainid_path: str | None = None
    selector_path: str | None = None
    amount_path: str | None = None
    spender_path: str | None = None

    if (
        field_format == EIP712Format.CALLDATA
        and field.params is not None
        and isinstance(field.params, ResolvedCallDataParameters)
    ):
        try:
            callee_path = _resolve_calldata_param_path(field.params.calleePath)
            chainid_path = _resolve_calldata_param_path(
                str(field.params.chainId) if field.params.chainId is not None else None  # type: ignore[arg-type]
            )
            selector_path = _resolve_calldata_param_path(
                str(field.params.selectorPath) if field.params.selectorPath is not None else None
            )
            amount_path = _resolve_calldata_param_path(
                str(field.params.amountPath) if field.params.amountPath is not None else None
            )
            spender_path = _resolve_calldata_param_path(
                str(field.params.spenderPath) if field.params.spenderPath is not None else None
            )
        except ValueError as e:
            return out.error(
                title="Calldata param error",
                message=str(e),
            )

    return InputEIP712MapperField(
        path=relative_path,
        label=field.label,
        assetPath=asset_path,
        format=field_format,
        nameTypes=name_types,
        nameSources=name_sources,
        calleePath=callee_path,
        chainIdPath=chainid_path,
        selectorPath=selector_path,
        amountPath=amount_path,
        spenderPath=spender_path,
    )


def _resolve_calldata_param_path(path_str: str | None) -> str | None:
    """Resolve a calldata parameter path string for the legacy format."""
    if path_str is None:
        return None
    parsed = to_path(path_str)
    if isinstance(parsed, DataPath):
        return str(to_relative(parsed))
    if isinstance(parsed, ContainerPath) and str(parsed) == "@.to":
        return "@.to"
    raise ValueError(f'Path "{path_str}" is not supported for calldata parameter conversion.')


def _convert_trusted_names_types(types: list[AddressNameType] | None) -> list[EIP712NameType] | None:
    """Convert v2 address name types to legacy EIP-712 name types."""
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
                name_types.append(EIP712NameType(str(name_type)))
    return name_types


def _convert_trusted_names_sources(
    sources: list[str] | None, names: list[EIP712NameType] | None
) -> list[EIP712NameSource] | None:
    """Convert v2 trusted name sources to legacy EIP-712 name sources."""
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
                    pass

    for name_source in sources:
        if name_source == "local":
            name_sources.append(EIP712NameSource.LOCAL_ADDRESS_BOOK)
        elif name_source in set(EIP712NameSource) and name_source not in name_sources:
            name_sources.append(EIP712NameSource(name_source))

    if not name_sources:
        name_sources = list(EIP712NameSource)
    return name_sources


# ---------------------------------------------------------------------------
# Converter class
# ---------------------------------------------------------------------------


@final
class ERC7730V2toEIP712Converter:
    """
    Converts a v2 ERC-7730 input descriptor with EIP-712 context to Ledger legacy EIP-712 descriptors.

    The conversion:
    1. Resolves the v2 input descriptor.
    2. Reconstructs ``EIP712Domain`` from domain info + deployments.
    3. Parses each ``display.formats`` key (an encodeType string) to rebuild the per-message schema.
    4. Converts v2 resolved display fields to ``InputEIP712MapperField``.
    5. Produces one ``InputEIP712DAppDescriptor`` per chain id.
    """

    def convert(
        self,
        input_descriptor: InputERC7730Descriptor,
        out: OutputAdder | None = None,
    ) -> dict[str, InputEIP712DAppDescriptor] | None:
        """Convert a v2 input descriptor to legacy EIP-712 descriptors.

        :param input_descriptor: a deserialized v2 input ERC-7730 descriptor
        :param out: error / warning handler (defaults to console)
        :return: dict mapping chain id strings to legacy descriptors, or ``None`` on error
        """
        if out is None:
            out = ConsoleOutputAdder()

        with ExceptionsToOutput(out):
            # Verify context is EIP-712
            if not isinstance(input_descriptor.context, InputEIP712Context):
                return out.error(
                    title="Wrong context type",
                    message="Descriptor context is not EIP-712; only EIP-712 descriptors can be converted.",
                )

            # Resolve the v2 descriptor
            resolved = ERC7730InputToResolved().convert(input_descriptor, out)
            if resolved is None:
                return None

            return self._convert_resolved(resolved, out)

        return None

    def _convert_resolved(
        self,
        descriptor: ResolvedERC7730Descriptor,
        out: OutputAdder,
    ) -> dict[str, InputEIP712DAppDescriptor] | None:
        context = descriptor.context
        if not isinstance(context, ResolvedEIP712Context):
            return out.error(
                title="Wrong context type",
                message="Resolved context is not EIP-712.",
            )

        domain = context.eip712.domain
        has_deployments = len(context.eip712.deployments) > 0

        # Get dapp name from domain
        dapp_name: str | None = domain.name if domain is not None else None
        if dapp_name is None:
            return out.error(
                title="Missing domain name",
                message="EIP-712 domain name is required for legacy EIP-712 conversion.",
            )

        # Get contract name from metadata
        contract_name = descriptor.metadata.owner
        if contract_name is None:
            return out.error(
                title="Missing owner",
                message="metadata.owner is required for legacy EIP-712 conversion.",
            )

        # Reconstruct EIP712Domain type
        domain_fields = _reconstruct_eip712_domain(domain, has_deployments, out)

        # Build messages from format keys
        messages: list[InputEIP712Message] = []
        for format_key, format_def in descriptor.display.formats.items():
            # Parse the encodeType key into primaryType + types dict
            schema_result = _build_schema(format_key, domain_fields, out)
            if schema_result is None:
                return None
            _primary_type, schema_types = schema_result

            # Convert fields
            output_fields: list[InputEIP712MapperField] = []
            for field in format_def.fields:
                if (converted := _convert_v2_field(field, out)) is None:
                    return None
                output_fields.extend(converted)

            label = format_def.intent if isinstance(format_def.intent, str) else _primary_type

            messages.append(
                InputEIP712Message(
                    schema=schema_types,
                    mapper=InputEIP712Mapper(label=label, fields=output_fields),
                )
            )

        # Build per-chain descriptors
        descriptors: dict[str, InputEIP712DAppDescriptor] = {}
        for deployment in context.eip712.deployments:
            chain_id = str(deployment.chainId)
            output_descriptor = self._build_network_descriptor(
                deployment, dapp_name, contract_name, messages, descriptors.get(chain_id), out
            )
            if output_descriptor is not None:
                descriptors[chain_id] = output_descriptor

        return descriptors

    @staticmethod
    def _build_network_descriptor(
        deployment: ResolvedDeployment,
        dapp_name: str,
        contract_name: str,
        messages: list[InputEIP712Message],
        descriptor: InputEIP712DAppDescriptor | None,
        out: OutputAdder,
    ) -> InputEIP712DAppDescriptor | None:
        if (network := ledger_network_id(deployment.chainId)) is None:
            out.error(
                title="Unsupported network",
                message=f"Network id {deployment.chainId} not supported.",
            )
            return descriptor

        contracts = descriptor.contracts if descriptor is not None else []
        contracts.append(
            InputEIP712Contract(
                address=deployment.address.lower(),
                contractName=contract_name,
                messages=messages,
            )
        )

        return InputEIP712DAppDescriptor(
            blockchainName=network,
            chainId=deployment.chainId,
            name=dapp_name,
            contracts=contracts,
        )
