from typing import assert_never, cast

from erc7730.common.output import OutputAdder
from erc7730.convert.resolved.constants import ConstantProvider
from erc7730.model.input.display import (
    InputAddressNameParameters,
    InputCallDataParameters,
    InputDateParameters,
    InputEnumParameters,
    InputFieldParameters,
    InputNftNameParameters,
    InputTokenAmountParameters,
    InputUnitParameters,
)
from erc7730.model.paths import DataPath
from erc7730.model.paths.path_ops import data_or_container_path_concat
from erc7730.model.resolved.display import (
    ResolvedAddressNameParameters,
    ResolvedCallDataParameters,
    ResolvedDateParameters,
    ResolvedEnumParameters,
    ResolvedFieldParameters,
    ResolvedNftNameParameters,
    ResolvedTokenAmountParameters,
    ResolvedUnitParameters,
)
from erc7730.model.resolved.path import ResolvedPath


def convert_field_parameters(
    prefix: DataPath, params: InputFieldParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedFieldParameters | None:
    match params:
        case None:
            return None
        case InputAddressNameParameters():
            return convert_address_name_parameters(prefix, params, constants, out)
        case InputCallDataParameters():
            return convert_calldata_parameters(prefix, params, constants, out)
        case InputTokenAmountParameters():
            return convert_token_amount_parameters(prefix, params, constants, out)
        case InputNftNameParameters():
            return convert_nft_parameters(prefix, params, constants, out)
        case InputDateParameters():
            return convert_date_parameters(prefix, params, constants, out)
        case InputUnitParameters():
            return convert_unit_parameters(prefix, params, constants, out)
        case InputEnumParameters():
            return convert_enum_parameters(prefix, params, constants, out)
        case _:
            assert_never(params)


def convert_address_name_parameters(
    prefix: DataPath, params: InputAddressNameParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedAddressNameParameters | None:
    return ResolvedAddressNameParameters(
        types=constants.resolve_or_none(params.types), sources=constants.resolve_or_none(params.sources)
    )


def convert_calldata_parameters(
    prefix: DataPath, params: InputCallDataParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedCallDataParameters | None:
    callee_path: ResolvedPath = cast(ResolvedPath, constants.resolve(params.calleePath))
    return ResolvedCallDataParameters(
        selector=constants.resolve_or_none(params.selector),
        calleePath=data_or_container_path_concat(prefix, callee_path),
    )


def convert_token_amount_parameters(
    prefix: DataPath, params: InputTokenAmountParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedTokenAmountParameters | None:
    token_path: ResolvedPath | None = cast(ResolvedPath | None, constants.resolve_or_none(params.tokenPath))
    return ResolvedTokenAmountParameters(
        tokenPath=None if token_path is None else data_or_container_path_concat(prefix, token_path),
        nativeCurrencyAddress=constants.resolve_or_none(params.nativeCurrencyAddress),  # type:ignore
        threshold=constants.resolve_or_none(params.threshold),
        message=constants.resolve_or_none(params.message),
    )


def convert_nft_parameters(
    prefix: DataPath, params: InputNftNameParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedNftNameParameters | None:
    collection_path: ResolvedPath = cast(ResolvedPath, constants.resolve(params.collectionPath))
    return ResolvedNftNameParameters(collectionPath=data_or_container_path_concat(prefix, collection_path))


def convert_date_parameters(
    prefix: DataPath, params: InputDateParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedDateParameters | None:
    return ResolvedDateParameters(encoding=constants.resolve(params.encoding))


def convert_unit_parameters(
    prefix: DataPath, params: InputUnitParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedUnitParameters | None:
    return ResolvedUnitParameters(
        base=constants.resolve(params.base),
        decimals=constants.resolve_or_none(params.decimals),
        prefix=constants.resolve_or_none(params.prefix),
    )


def convert_enum_parameters(
    prefix: DataPath, params: InputEnumParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedEnumParameters | None:
    return ResolvedEnumParameters.model_validate({"$ref": params.ref})  # TODO must inline here
