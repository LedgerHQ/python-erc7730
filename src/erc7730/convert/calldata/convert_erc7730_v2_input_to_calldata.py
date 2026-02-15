"""
Conversion of v2 ERC-7730 input descriptors to calldata descriptors.

In v2, the ABI is no longer embedded in the contract context. Instead, the display.formats keys are
human-readable ABI signatures (e.g., "cooldownShares(uint256 shares)") from which Function objects
can be parsed and selectors computed. This module provides the v2-specific entry point and conversion
logic.
"""

import hashlib
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
from erc7730.convert.calldata.v1.abi import ABITree, function_to_abi_tree
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
    CalldataDescriptorV1,
)
from erc7730.model.calldata.types import TrustedNameSource, TrustedNameType
from erc7730.model.calldata.v1.instruction import (
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
    CalldataDescriptorParamNFTV1,
    CalldataDescriptorParamRawV1,
    CalldataDescriptorParamTokenAmountV1,
    CalldataDescriptorParamTrustedNameV1,
    CalldataDescriptorParamUnitV1,
    CalldataDescriptorParamV1,
)
from erc7730.model.calldata.v1.value import (
    CalldataDescriptorValueConstantV1,
    CalldataDescriptorValueV1,
    CalldataDescriptorTypeFamily,
)
from erc7730.model.display import AddressNameType
from erc7730.model.input.v2.context import InputContractContext
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.input.v2.format import DateEncoding, FieldFormat
from erc7730.model.paths import ContainerPath, DataPath
from erc7730.model.paths.path_parser import to_path
from erc7730.model.resolved.v2.context import (
    ResolvedContractContext,
    ResolvedDeployment,
)
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.v2.display import (
    ResolvedFieldDescription,
    ResolvedFieldGroup,
    ResolvedFormat,
)
from erc7730.model.types import Address, HexStr, ScalarType, Selector


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
        if (output_fields := _convert_v2_field(abi=abi_tree, field=input_field, enums=enums_by_id, out=out)) is None:
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
        contract_name=descriptor.context.id,
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
    abi: ABITree,
    field: ResolvedFieldDescription | ResolvedFieldGroup,
    enums: dict[str, int],
    out: OutputAdder,
) -> list[CalldataDescriptorInstructionFieldV1] | None:
    """
    Convert a v2 resolved field to calldata descriptor field instructions.

    Fields with ``visible == "never"`` are skipped — they correspond to v1 ``excluded`` fields
    that were never included in calldata output.

    :param abi: function ABI tree
    :param field: v2 resolved field
    :param enums: mapping of source descriptor enum ids to calldata descriptor enum ids
    :param out: error handler
    :return: 1 or more calldata field instructions, or None on error
    """
    if isinstance(field, ResolvedFieldDescription):
        # Skip hidden fields (v2 equivalent of v1 "excluded" fields)
        if field.visible == "never":
            return []
        if (param := _convert_v2_param(abi=abi, field=field, enums=enums, out=out)) is None:
            return None
        return [CalldataDescriptorInstructionFieldV1(name=field.label, param=param)]
    elif isinstance(field, ResolvedFieldGroup):
        # In v1 protocol, nested fields are flattened
        instructions: list[CalldataDescriptorInstructionFieldV1] = []
        for nested_field in field.fields:
            if (
                nested_instructions := _convert_v2_field(abi=abi, field=nested_field, enums=enums, out=out)
            ) is None:
                return None
            instructions.extend(nested_instructions)
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
    abi: ABITree,
    out: OutputAdder,
) -> CalldataDescriptorValueV1 | None:
    """
    Convert a v2 resolved path/value to a calldata protocol value.

    In v2, the resolved model stores path as a string and value as a scalar.
    We parse the string path back into DataPath/ContainerPath objects and reuse the v1 binary encoding.

    :param path_str: v2 resolved path string (e.g. "#.amount", "@.from")
    :param value: v2 resolved constant value
    :param format_type: field format type
    :param abi: function ABI tree
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
            return convert_data_path(parsed_path, abi, out)
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
    abi: ABITree,
    field: ResolvedFieldDescription,
    enums: dict[str, int],
    out: OutputAdder,
) -> CalldataDescriptorParamV1 | None:
    """
    Convert v2 resolved field parameters to a calldata descriptor field parameter.

    This mirrors the v1 convert_param logic but works with v2 resolved types.

    :param abi: function ABI tree
    :param field: v2 resolved field description
    :param enums: mapping of source descriptor enum ids to calldata descriptor enum ids
    :param out: error handler
    :return: calldata protocol field parameter or None on error
    """
    path_str = str(field.path) if field.path is not None else None
    if (value := _convert_v2_value(path_str, field.value, field.format, abi, out)) is None:
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
            collection_path_str = getattr(field.params, "collection", None) or getattr(
                field.params, "collectionPath", None
            )
            if collection_path_str is None:
                return out.error(
                    title="Missing collection",
                    message="NFT name parameters must include a collection or collectionPath.",
                )
            if (collection_value := _convert_v2_value(str(collection_path_str), None, None, abi, out)) is None:
                return None
            return CalldataDescriptorParamNFTV1(value=value, collection=collection_value)

        case FieldFormat.CALL_DATA:
            if field.params is None:
                return out.error(
                    title="Missing calldata parameters",
                    message="Calldata format requires parameters.",
                )
            callee_str = getattr(field.params, "callee", None) or getattr(field.params, "calleePath", None)
            if callee_str is None:
                return out.error(
                    title="Missing callee",
                    message="Calldata parameters must include a callee or calleePath.",
                )
            if (callee := _convert_v2_value(str(callee_str), None, None, abi, out)) is None:
                return None

            selector_str = getattr(field.params, "selector", None) or getattr(field.params, "selectorPath", None)
            selector_val = _convert_v2_value(str(selector_str), None, None, abi, out) if selector_str else None

            chain_id_val = None
            chain_id_attr = getattr(field.params, "chainId", None) or getattr(field.params, "chainIdPath", None)
            if chain_id_attr:
                chain_id_val = _convert_v2_value(str(chain_id_attr), None, None, abi, out)

            amount_str = getattr(field.params, "amount", None) or getattr(field.params, "amountPath", None)
            amount_val = _convert_v2_value(str(amount_str), None, None, abi, out) if amount_str else None

            spender_str = getattr(field.params, "spender", None) or getattr(field.params, "spenderPath", None)
            spender_val = _convert_v2_value(str(spender_str), None, None, abi, out) if spender_str else None

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

        case FieldFormat.TOKEN_AMOUNT:
            token_path: CalldataDescriptorValueV1 | None = None
            native_currencies: list[Address] | None = None
            threshold: HexStr | None = None
            above_threshold_message: str | None = None

            if field.params is not None:
                token = getattr(field.params, "token", None)
                token_path_str = getattr(field.params, "tokenPath", None)

                if token is not None:
                    token_value_str = str(token)
                    # Token is an address, convert as path if it's a path, otherwise as constant
                    if token_value_str.startswith("#.") or token_value_str.startswith("@."):
                        token_path = _convert_v2_value(token_value_str, None, None, abi, out)
                    else:
                        # It's a resolved address constant — encode as constant value
                        raw = encode_value(token_value_str, ABIDataType.ADDRESS, out)
                        if raw is not None:
                            token_path = CalldataDescriptorValueConstantV1(
                                type_family=CalldataDescriptorTypeFamily.ADDRESS,
                                type_size=20,
                                value=token_value_str,
                                raw=raw,
                            )
                elif token_path_str is not None:
                    token_path = _convert_v2_value(str(token_path_str), None, None, abi, out)

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
