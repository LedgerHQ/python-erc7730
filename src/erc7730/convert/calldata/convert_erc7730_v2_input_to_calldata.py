"""
Conversion of v2 ERC-7730 input descriptors to calldata descriptors.

In v2, the ABI is no longer embedded in the contract context. Instead, the display.formats keys are
human-readable ABI signatures (e.g., "cooldownShares(uint256 shares)") from which Function objects
can be parsed and selectors computed. This module provides the v2-specific entry point and conversion
logic.
"""

import hashlib
from collections.abc import Callable
from typing import cast

from pydantic_string_url import HttpUrl

from erc7730.common.abi import (
    ABIDataType,
    parse_signature,
    reduce_signature,
    signature_to_selector,
)
from erc7730.common.binary import from_hex
from erc7730.common.ledger import ledger_network_id
from erc7730.common.options import first_not_none
from erc7730.common.output import ConsoleOutputAdder, OutputAdder, exception_to_output
from erc7730.convert.calldata.v1.abi import function_to_abi_tree
from erc7730.convert.calldata.v1.eip712_path import convert_eip712_data_path
from erc7730.convert.calldata.v1.eip712_schema import ReconstructedSchema, reconstruct_schema
from erc7730.convert.calldata.v1.enum import convert_enums
from erc7730.convert.calldata.v1.path import (
    convert_container_path,
    convert_data_path,
)
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import (
    ERC7730InputToResolved,
)
from erc7730.convert.resolved.v2.values import encode_value
from erc7730.model.abi import Function
from erc7730.model.calldata.descriptor import (
    CalldataDescriptor,
    CalldataDescriptorEIP712V1,
    CalldataDescriptorV1,
)
from erc7730.model.calldata.types import TrustedNameSource, TrustedNameType
from erc7730.model.calldata.v1.eip712 import (
    CalldataDescriptorInstructionEIP712SchemaV1,
)
from erc7730.model.calldata.v1.instruction import (
    CalldataDescriptorInstructionEIP712MessageInfoV1,
    CalldataDescriptorInstructionFieldV1,
    CalldataDescriptorInstructionTransactionInfoV1,
)
from erc7730.model.calldata.v1.param import (
    CalldataDescriptorDateType,
    CalldataDescriptorParamAmountV1,
    CalldataDescriptorParamCalldataV1,
    CalldataDescriptorParamDatetimeV1,
    CalldataDescriptorParamDurationV1,
    CalldataDescriptorParamEnumV1,
    CalldataDescriptorParamNetworkV1,
    CalldataDescriptorParamNFTV1,
    CalldataDescriptorParamRawV1,
    CalldataDescriptorParamTokenAmountV1,
    CalldataDescriptorParamTokenV1,
    CalldataDescriptorParamTrustedNameV1,
    CalldataDescriptorParamUnitV1,
    CalldataDescriptorParamV1,
)
from erc7730.model.calldata.v1.value import (
    CalldataDescriptorTypeFamily,
    CalldataDescriptorValueConstantV1,
    CalldataDescriptorValuePathV1,
    CalldataDescriptorValueV1,
)
from erc7730.model.display import AddressNameType
from erc7730.model.input.v2.context import InputContractContext, InputEIP712Context
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.input.v2.format import DateEncoding, FieldFormat
from erc7730.model.paths import ContainerPath, DataPath
from erc7730.model.paths.path_parser import to_path
from erc7730.model.resolved.display import ResolvedValueConstant, ResolvedValuePath
from erc7730.model.resolved.v2.context import (
    ResolvedContractContext,
    ResolvedDeployment,
    ResolvedEIP712Context,
)
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.v2.display import (
    ResolvedCallDataParameters,
    ResolvedFieldDescription,
    ResolvedFieldGroup,
    ResolvedFormat,
    ResolvedNftNameParameters,
    ResolvedVisibilityConditions,
)
from erc7730.model.types import Address, HexStr, ScalarType, Selector

# Converts a resolved data path to a calldata protocol value; contract binding navigates the ABI tree, EIP-712
# binding navigates the reconstructed message value tree.
DataPathConverter = Callable[[DataPath, OutputAdder], CalldataDescriptorValuePathV1 | None]


def erc7730_v2_descriptor_to_calldata_descriptors(
    input_descriptor: InputERC7730Descriptor,
    source: HttpUrl | None = None,
    chain_id: int | None = None,
) -> list[CalldataDescriptor]:
    """
    Generate output calldata descriptors from a v2 input ERC-7730 descriptor with contract context.

    If descriptor is invalid, an empty list is returned. If the descriptor is partially invalid, a partial list is
    returned. Errors are logged as warnings.

    :param input_descriptor: deserialized v2 input ERC-7730 descriptor
    :param source: source of the descriptor file
    :param chain_id: if set, only emit calldata descriptors for given chain IDs
    :return: output calldata descriptors (1 per chain + selector)
    """
    out = ConsoleOutputAdder()

    try:
        if isinstance(input_descriptor.context, InputEIP712Context):
            return _convert_eip712_descriptors(input_descriptor, source, chain_id, out)

        if not isinstance(input_descriptor.context, InputContractContext):
            return []

        # Parse format keys (human-readable ABI signatures) into Function objects
        abis: dict[Selector, Function] = {}
        for format_key in input_descriptor.display.formats:
            if format_key.startswith("0x"):
                out.warning(f"Format key '{format_key}' is already a selector, cannot reconstruct ABI - skipping")
                continue
            try:
                func = parse_signature(format_key)
                reduced = reduce_signature(format_key)
                selector = Selector(signature_to_selector(reduced))
                abis[selector] = func
            except ValueError as e:
                out.warning(f"Failed to parse format key '{format_key}': {e}")
                continue

        if not abis:
            out.warning("No valid function signatures found in display.formats keys")
            return []

        # Check chain_id filter against deployments
        if chain_id is not None:
            deployment_chain_ids = {d.chainId for d in input_descriptor.context.contract.deployments}
            if chain_id not in deployment_chain_ids:
                return []

        # Resolve the v2 descriptor
        if (resolved_descriptor := ERC7730InputToResolved().convert(input_descriptor, out)) is None:
            return []

        context = cast(ResolvedContractContext, resolved_descriptor.context)

        output_descriptors: list[CalldataDescriptor] = []

        for deployment in context.contract.deployments:
            if chain_id is not None and chain_id != deployment.chainId:
                continue

            if ledger_network_id(deployment.chainId) is None:
                out.warning(f"Chain id {deployment.chainId} is not known, skipping it")
                continue

            for selector, format in resolved_descriptor.display.formats.items():
                if (abi := abis.get(selector)) is None:
                    out.error(
                        title="Invalid selector",
                        message=f"Selector {selector} not found in parsed ABI signatures.",
                    )
                    continue

                descriptor = _convert_v2_selector(
                    descriptor=resolved_descriptor,
                    deployment=deployment,
                    selector=selector,
                    format=format,
                    abi=abi,
                    source=source,
                    out=out,
                )

                if descriptor is not None:
                    output_descriptors.append(descriptor)

        return output_descriptors

    except Exception as e:
        out.warning(f"Error processing v2 ERC-7730 file {source}, skipping it")
        exception_to_output(e, out)

    return []


def _convert_v2_selector(
    descriptor: ResolvedERC7730Descriptor,
    deployment: ResolvedDeployment,
    selector: Selector,
    format: ResolvedFormat,
    abi: Function,
    source: HttpUrl | None,
    out: OutputAdder,
) -> CalldataDescriptor | None:
    """
    Generate output calldata descriptor for a single v2 selector.

    :param descriptor: resolved v2 source ERC-7730 descriptor
    :param deployment: chain id / contract address for which the descriptor is generated
    :param selector: function selector
    :param format: v2 resolved format for the selector
    :param abi: parsed ABI Function from format key signature
    :param source: source of the descriptor file
    :param out: error handler
    :return: output calldata descriptor or None if invalid
    """
    abi_tree = function_to_abi_tree(abi)

    def convert_path(data_path: DataPath, out: OutputAdder) -> CalldataDescriptorValuePathV1 | None:
        return convert_data_path(data_path, abi_tree, out)

    creator_legal_name: str | None = None
    creator_url: str | None = None
    deploy_date: str | None = None
    if descriptor.metadata.info is not None:
        creator_legal_name = descriptor.metadata.owner
        creator_url = str(descriptor.metadata.info.url) if descriptor.metadata.info.url else None
        deploy_date = (
            descriptor.metadata.info.deploymentDate.strftime("%Y-%m-%dT%H:%M:%SZ")
            if descriptor.metadata.info.deploymentDate
            else None
        )

    # Use v1 convert_enums — v2 ResolvedDeployment is duck-type compatible with v1
    enums = convert_enums(deployment, selector, descriptor.metadata.enums)  # type: ignore[arg-type]
    enums_by_id = {enum.enum_id: enum.id for enum in enums}

    fields: list[CalldataDescriptorInstructionFieldV1] = []
    for input_field in format.fields:
        if (output_fields := _convert_v2_field(convert_path, input_field, enums_by_id, out)) is None:
            return None
        fields.extend(output_fields)

    hash = hashlib.sha3_256()
    for field in fields:
        hash.update(from_hex(field.descriptor))

    transaction_info = CalldataDescriptorInstructionTransactionInfoV1(
        chain_id=deployment.chainId,
        address=deployment.address,
        selector=selector,
        hash=hash.digest().hex(),
        operation_type=first_not_none(format.intent, format.id, selector),  # type:ignore
        creator_name=descriptor.metadata.owner,
        creator_legal_name=creator_legal_name,
        creator_url=creator_url,
        contract_name=descriptor.metadata.contractName or descriptor.context.id,
        deploy_date=deploy_date,
    )

    return CalldataDescriptorV1(
        source=source,
        network=cast(str, ledger_network_id(deployment.chainId)),
        chain_id=deployment.chainId,
        address=deployment.address,
        selector=selector,
        transaction_info=transaction_info,
        enums=enums,
        fields=fields,
    )


# --- V2 field conversion ---


def _convert_v2_field(
    convert_path: DataPathConverter,
    field: ResolvedFieldDescription | ResolvedFieldGroup,
    enums: dict[str, int],
    out: OutputAdder,
) -> list[CalldataDescriptorInstructionFieldV1] | None:
    """
    Convert a v2 resolved field to calldata descriptor field instructions.

    Fields with ``visible == "never"`` are skipped — they correspond to v1 ``excluded`` fields
    that were never included in calldata output.

    :param convert_path: strategy converting a resolved data path to a calldata value (ABI or EIP-712 navigation)
    :param field: v2 resolved field
    :param enums: mapping of source descriptor enum ids to calldata descriptor enum ids
    :param out: error handler
    :return: 1 or more calldata field instructions, or None on error
    """
    if isinstance(field, ResolvedFieldDescription):
        # Skip hidden fields (v2 equivalent of v1 "excluded" fields)
        if field.visible == "never":
            return []
        if field.label is None:
            if isinstance(field.visible, ResolvedVisibilityConditions) and field.visible.mustBe is not None:
                return out.error(
                    title="Unsupported visible value",
                    message="Fields with mustBe visibility conditions are not supported in calldata conversion.",
                )
            return out.error(
                title="Missing field label",
                message="Field label is mandatory for calldata conversion.",
            )
        if (param := _convert_v2_param(convert_path=convert_path, field=field, enums=enums, out=out)) is None:
            return None
        return [CalldataDescriptorInstructionFieldV1(name=field.label, param=param)]
    elif isinstance(field, ResolvedFieldGroup):
        # TODO the protocol defines a PARAM_GROUP struct (with ITERATION_TYPE) for nested fields; for now nested
        #      fields are flattened, matching the existing v1 contract behavior. Revisit once PARAM_GROUP device
        #      semantics (notably BUNDLED iteration) are finalized in the Ethereum app specifications.
        instructions: list[CalldataDescriptorInstructionFieldV1] = []
        for nested_field in field.fields:
            nested = _convert_v2_field(convert_path=convert_path, field=nested_field, enums=enums, out=out)
            if nested is None:
                return None
            instructions.extend(nested)
        return instructions
    else:
        return out.error(
            title="Unknown field type",
            message=f"Unexpected field type: {type(field)}",
        )


def _convert_v2_value(
    path_str: str | None,
    value: ScalarType | None,
    format_type: FieldFormat | None,
    convert_path: DataPathConverter,
    out: OutputAdder,
) -> CalldataDescriptorValueV1 | None:
    """
    Convert a v2 resolved path/value to a calldata protocol value.

    In v2, the resolved model stores path as a string and value as a scalar.
    We parse the string path back into DataPath/ContainerPath objects and reuse the v1 binary encoding.

    :param path_str: v2 resolved path string (e.g. "#.amount", "@.from")
    :param value: v2 resolved constant value
    :param format_type: field format type
    :param convert_path: strategy converting a resolved data path to a calldata value
    :param out: error handler
    :return: calldata protocol value or None on error
    """
    if path_str is not None:
        try:
            parsed_path = to_path(str(path_str))
        except (ValueError, Exception) as e:
            return out.error(
                title="Invalid path",
                message=f'Failed to parse path "{path_str}": {e}',
            )

        if isinstance(parsed_path, ContainerPath):
            return convert_container_path(parsed_path, out)
        elif isinstance(parsed_path, DataPath):
            return convert_path(parsed_path, out)
        else:
            return out.error(
                title="Unsupported path type",
                message=f'Descriptor paths are not supported in calldata conversion: "{path_str}"',
            )

    elif value is not None:
        # Reconstruct a v1-compatible constant value
        abi_type = _format_to_abi_type(format_type)
        raw = encode_value(value, abi_type, out)
        if raw is None:
            return None
        return CalldataDescriptorValueConstantV1(
            type_family=CalldataDescriptorTypeFamily[abi_type.name],
            type_size=len(raw) // 2 - 1,
            value=value,
            raw=raw,
        )

    return out.error(
        title="Invalid field",
        message="Field must have either a path or a value.",
    )


def _format_to_abi_type(format_type: FieldFormat | None) -> ABIDataType:
    """Map a field format to the expected ABI data type (for constant value encoding)."""
    match format_type:
        case None | FieldFormat.RAW:
            return ABIDataType.STRING
        case (
            FieldFormat.AMOUNT
            | FieldFormat.TOKEN_AMOUNT
            | FieldFormat.DURATION
            | FieldFormat.DATE
            | FieldFormat.UNIT
            | FieldFormat.NFT_NAME
            | FieldFormat.ENUM
        ):
            return ABIDataType.UINT
        case FieldFormat.ADDRESS_NAME | FieldFormat.INTEROPERABLE_ADDRESS_NAME:
            return ABIDataType.ADDRESS
        case FieldFormat.CALL_DATA:
            return ABIDataType.BYTES
        case FieldFormat.TOKEN_TICKER:
            return ABIDataType.ADDRESS
        case FieldFormat.CHAIN_ID:
            return ABIDataType.UINT
        case _:
            return ABIDataType.STRING


def _convert_v2_param(
    convert_path: DataPathConverter,
    field: ResolvedFieldDescription,
    enums: dict[str, int],
    out: OutputAdder,
) -> CalldataDescriptorParamV1 | None:
    """
    Convert v2 resolved field parameters to a calldata descriptor field parameter.

    This mirrors the v1 convert_param logic but works with v2 resolved types.

    :param convert_path: strategy converting a resolved data path to a calldata value (ABI or EIP-712 navigation)
    :param field: v2 resolved field description
    :param enums: mapping of source descriptor enum ids to calldata descriptor enum ids
    :param out: error handler
    :return: calldata protocol field parameter or None on error
    """
    path_str = str(field.path) if field.path is not None else None
    if (value := _convert_v2_value(path_str, field.value, field.format, convert_path, out)) is None:
        return None

    def _convert_resolved_value(
        resolved_value: ResolvedValuePath | ResolvedValueConstant | None,
        abi_type: ABIDataType,
    ) -> CalldataDescriptorValueV1 | None:
        if resolved_value is None:
            return None
        if isinstance(resolved_value, ResolvedValuePath):
            return _convert_v2_value(str(resolved_value.path), None, None, convert_path, out)
        if isinstance(resolved_value, ResolvedValueConstant):
            raw = encode_value(resolved_value.value, abi_type, out)
            if raw is None:
                return None
            return CalldataDescriptorValueConstantV1(
                type_family=CalldataDescriptorTypeFamily[abi_type.name],
                type_size=len(raw) // 2 - 1,
                value=resolved_value.value,
                raw=raw,
            )
        return None

    match field.format:
        case None | FieldFormat.RAW:
            return CalldataDescriptorParamRawV1(value=value)

        case FieldFormat.ADDRESS_NAME:
            types: list[TrustedNameType] = []
            sources: list[TrustedNameSource] = []
            sender_addresses: list[Address] | None = None

            if field.params is not None:
                address_params = field.params
                if (input_types := getattr(address_params, "types", None)) is not None:
                    for input_type in input_types:
                        if input_type == AddressNameType.CONTRACT:
                            types.append(TrustedNameType.SMART_CONTRACT)
                        else:
                            types.append(TrustedNameType(input_type))

                for type_ in types:
                    match type_:
                        case TrustedNameType.EOA | TrustedNameType.WALLET | TrustedNameType.COLLECTION:
                            sources.append(TrustedNameSource.ENS)
                            sources.append(TrustedNameSource.UNSTOPPABLE_DOMAIN)
                            sources.append(TrustedNameSource.FREENAME)
                        case TrustedNameType.SMART_CONTRACT | TrustedNameType.TOKEN:
                            sources.append(TrustedNameSource.CRYPTO_ASSET_LIST)
                        case TrustedNameType.CONTEXT_ADDRESS:
                            sources.append(TrustedNameSource.DYNAMIC_RESOLVER)
                        case _:
                            pass

                if (input_sources := getattr(address_params, "sources", None)) is not None:
                    for input_source in input_sources:
                        if input_source.lower() == "local":
                            sources.append(TrustedNameSource.LOCAL_ADDRESS_BOOK)
                            sources.append(TrustedNameSource.MULTISIG_ADDRESS_BOOK)
                        if input_source.lower() in set(TrustedNameSource):
                            sources.append(TrustedNameSource(input_source.lower()))

                sender_addresses = getattr(address_params, "senderAddress", None)

            types = list(TrustedNameType) if not types else list(dict.fromkeys(types))
            sources = list(TrustedNameSource) if not sources else list(dict.fromkeys(sources))

            return CalldataDescriptorParamTrustedNameV1(
                value=value, types=types, sources=sources, sender_addresses=sender_addresses
            )

        case FieldFormat.ENUM:
            if field.params is None:
                return out.error(
                    title="Missing enum parameters",
                    message="Enum format requires parameters.",
                )
            # V2 enum params have ref (e.g., "$.metadata.enums.myEnum")
            # Extract the enum ID from the ref path
            ref = getattr(field.params, "ref", None)
            if ref is None:
                return out.error(
                    title="Missing enum reference",
                    message="Enum parameters must include a $ref.",
                )
            enum_id_str = str(ref).split(".")[-1]
            if (enum_id := enums.get(enum_id_str)) is None:
                return out.error(
                    title="Invalid enum id",
                    message=f"Failed finding descriptor id for enum {enum_id_str}, please report this bug",
                )
            return CalldataDescriptorParamEnumV1(value=value, id=enum_id)

        case FieldFormat.UNIT:
            if field.params is None:
                return out.error(
                    title="Missing unit parameters",
                    message="Unit format requires parameters.",
                )
            return CalldataDescriptorParamUnitV1(
                value=value,
                base=getattr(field.params, "base", ""),
                decimals=getattr(field.params, "decimals", None),
                prefix=getattr(field.params, "prefix", None),
            )

        case FieldFormat.DURATION:
            return CalldataDescriptorParamDurationV1(value=value)

        case FieldFormat.NFT_NAME:
            if field.params is None:
                return out.error(
                    title="Missing NFT parameters",
                    message="NFT name format requires parameters.",
                )
            if not isinstance(field.params, ResolvedNftNameParameters):
                return out.error(
                    title="Missing collection",
                    message="NFT name parameters must include a resolved collection value.",
                )
            if (collection_value := _convert_resolved_value(field.params.collection, ABIDataType.ADDRESS)) is None:
                return None
            return CalldataDescriptorParamNFTV1(value=value, collection=collection_value)

        case FieldFormat.CALL_DATA:
            if field.params is None:
                return out.error(
                    title="Missing calldata parameters",
                    message="Calldata format requires parameters.",
                )
            if not isinstance(field.params, ResolvedCallDataParameters):
                return out.error(
                    title="Missing callee",
                    message="Calldata parameters must include a resolved callee value.",
                )

            if (callee := _convert_resolved_value(field.params.callee, ABIDataType.ADDRESS)) is None:
                return None

            selector_val = _convert_resolved_value(field.params.selector, ABIDataType.STRING)

            # v2 calldata params may not define chainId; keep compatibility with both models.
            chain_id_val = _convert_resolved_value(getattr(field.params, "chainId", None), ABIDataType.UINT)

            amount_val = _convert_resolved_value(field.params.amount, ABIDataType.UINT)

            spender_val = _convert_resolved_value(field.params.spender, ABIDataType.ADDRESS)

            return CalldataDescriptorParamCalldataV1(
                value=value,
                callee=callee,
                selector=selector_val,
                chain_id=chain_id_val,
                amount=amount_val,
                spender=spender_val,
            )

        case FieldFormat.DATE:
            if field.params is None:
                return out.error(
                    title="Missing date parameters",
                    message="Date format requires parameters.",
                )
            encoding = getattr(field.params, "encoding", None)
            if encoding == DateEncoding.TIMESTAMP:
                date_type = CalldataDescriptorDateType.UNIX
            elif encoding == DateEncoding.BLOCKHEIGHT:
                date_type = CalldataDescriptorDateType.BLOCK_HEIGHT
            else:
                return out.error(
                    title="Unsupported date encoding",
                    message=f"Date encoding '{encoding}' is not supported.",
                )
            return CalldataDescriptorParamDatetimeV1(value=value, date_type=date_type)

        case FieldFormat.AMOUNT:
            return CalldataDescriptorParamAmountV1(value=value)

        case FieldFormat.TOKEN_TICKER:
            # tokenTicker maps to PARAM_TOKEN: the field value is the token address, ticker is resolved by the device.
            # chainId/chainIdPath have no equivalent tag in PARAM_TOKEN, so they cannot be encoded and are ignored.
            if field.params is not None and (
                getattr(field.params, "chainId", None) is not None
                or getattr(field.params, "chainIdPath", None) is not None
            ):
                out.warning(
                    "tokenTicker chainId/chainIdPath cannot be encoded in the PARAM_TOKEN struct and will be ignored."
                )
            # native_currencies is left unset: PARAM_TOKEN supports NATIVE_CURRENCY, but tokenTicker has no such param.
            return CalldataDescriptorParamTokenV1(value=value)

        case FieldFormat.CHAIN_ID:
            # chainId maps to PARAM_NETWORK: the field value is the chain ID, network name is resolved by the device.
            return CalldataDescriptorParamNetworkV1(value=value)

        case FieldFormat.TOKEN_AMOUNT:
            token_path: CalldataDescriptorValueV1 | None = None
            native_currencies: list[Address] | None = None
            threshold: HexStr | None = None
            above_threshold_message: str | None = None

            if field.params is not None:
                token = getattr(field.params, "token", None)
                token_path = _convert_resolved_value(token, ABIDataType.ADDRESS)

                threshold = getattr(field.params, "threshold", None)
                native_currencies = getattr(field.params, "nativeCurrencyAddress", None)
                above_threshold_message = getattr(field.params, "message", None)

            return CalldataDescriptorParamTokenAmountV1(
                value=value,
                token=token_path,
                native_currencies=native_currencies,
                threshold=threshold,
                above_threshold_message=above_threshold_message,
            )

        case _:
            return out.error(
                title="Unsupported format",
                message=f"Field format '{field.format}' is not supported for calldata conversion.",
            )


# --- EIP-712 message conversion ("EIP712 v2" in the Ethereum app specifications) ---


def _convert_eip712_descriptors(
    input_descriptor: InputERC7730Descriptor,
    source: HttpUrl | None,
    chain_id: int | None,
    out: OutputAdder,
) -> list[CalldataDescriptor]:
    """
    Generate calldata descriptors for a v2 input ERC-7730 descriptor with EIP-712 context.

    Unlike the contract binding (which navigates serialized calldata via the ABI), the EIP-712 binding reconstructs
    the message schema from the ``display.formats`` encodeType keys and navigates the message value tree.

    :param input_descriptor: deserialized v2 input ERC-7730 descriptor with EIP-712 context
    :param source: source of the descriptor file
    :param chain_id: if set, only emit descriptors for the given chain id
    :param out: error handler
    :return: output calldata descriptors (1 per chain + message primary type)
    """
    context = input_descriptor.context
    if not isinstance(context, InputEIP712Context):
        return []

    if chain_id is not None:
        deployment_chain_ids = {d.chainId for d in context.eip712.deployments}
        if chain_id not in deployment_chain_ids:
            return []

    if (resolved_descriptor := ERC7730InputToResolved().convert(input_descriptor, out)) is None:
        return []

    resolved_context = cast(ResolvedEIP712Context, resolved_descriptor.context)
    domain = resolved_context.eip712.domain
    has_deployments = len(resolved_context.eip712.deployments) > 0

    output_descriptors: list[CalldataDescriptor] = []

    for deployment in resolved_context.eip712.deployments:
        if chain_id is not None and chain_id != deployment.chainId:
            continue

        if ledger_network_id(deployment.chainId) is None:
            out.warning(f"Chain id {deployment.chainId} is not known, skipping it")
            continue

        for encode_type_key, format in resolved_descriptor.display.formats.items():
            schema = reconstruct_schema(str(encode_type_key), domain, has_deployments, out)
            if schema is None:
                continue

            descriptor = _convert_eip712_message(
                descriptor=resolved_descriptor,
                deployment=deployment,
                schema=schema,
                format=format,
                source=source,
                out=out,
            )

            if descriptor is not None:
                output_descriptors.append(descriptor)

    return output_descriptors


def _convert_eip712_message(
    descriptor: ResolvedERC7730Descriptor,
    deployment: ResolvedDeployment,
    schema: ReconstructedSchema,
    format: ResolvedFormat,
    source: HttpUrl | None,
    out: OutputAdder,
) -> CalldataDescriptor | None:
    """
    Generate a calldata descriptor for a single EIP-712 message primary type.

    :param descriptor: resolved v2 source ERC-7730 descriptor
    :param deployment: chain id / verifying contract address for which the descriptor is generated
    :param schema: reconstructed EIP-712 schema (structs + primary type hash)
    :param format: v2 resolved format for the message
    :param source: source of the descriptor file
    :param out: error handler
    :return: output calldata descriptor or None if invalid
    """

    def convert_path(data_path: DataPath, out: OutputAdder) -> CalldataDescriptorValuePathV1 | None:
        return convert_eip712_data_path(data_path, schema.primary_type, schema.types, out)

    creator_legal_name: str | None = None
    creator_url: str | None = None
    deploy_date: str | None = None
    if descriptor.metadata.info is not None:
        creator_legal_name = descriptor.metadata.owner
        creator_url = str(descriptor.metadata.info.url) if descriptor.metadata.info.url else None
        deploy_date = (
            descriptor.metadata.info.deploymentDate.strftime("%Y-%m-%dT%H:%M:%SZ")
            if descriptor.metadata.info.deploymentDate
            else None
        )

    # TODO the ENUM_VALUE struct carries a SELECTOR tag whose meaning for EIP-712 messages is not defined in the
    #      specification; a zeroed selector is used until it is clarified.
    enum_selector = Selector("0x00000000")
    enums = convert_enums(deployment, enum_selector, descriptor.metadata.enums)  # type: ignore[arg-type]
    enums_by_id = {enum.enum_id: enum.id for enum in enums}

    fields: list[CalldataDescriptorInstructionFieldV1] = []
    for input_field in format.fields:
        if (output_fields := _convert_v2_field(convert_path, input_field, enums_by_id, out)) is None:
            return None
        fields.extend(output_fields)

    hash = hashlib.sha3_256()
    for field in fields:
        hash.update(from_hex(field.descriptor))

    schema_info = CalldataDescriptorInstructionEIP712SchemaV1(structs=schema.structs)

    message_info = CalldataDescriptorInstructionEIP712MessageInfoV1(
        chain_id=deployment.chainId,
        address=deployment.address,
        primary_type_hash=schema.primary_type_hash,
        hash=hash.digest().hex(),
        operation_type=first_not_none(format.intent, format.id, schema.primary_type),  # type: ignore[arg-type]
        creator_name=descriptor.metadata.owner,
        creator_legal_name=creator_legal_name,
        creator_url=creator_url,
        contract_name=descriptor.metadata.contractName or descriptor.context.id,
        deploy_date=deploy_date,
    )

    return CalldataDescriptorEIP712V1(
        source=source,
        network=cast(str, ledger_network_id(deployment.chainId)),
        chain_id=deployment.chainId,
        address=deployment.address,
        primary_type_hash=schema.primary_type_hash,
        schema_info=schema_info,
        message_info=message_info,
        enums=enums,
        fields=fields,
    )
