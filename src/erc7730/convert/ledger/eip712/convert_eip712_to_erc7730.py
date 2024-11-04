from typing import assert_never, final, override

from eip712.model.resolved.descriptor import ResolvedEIP712DAppDescriptor
from eip712.model.resolved.message import ResolvedEIP712MapperField
from eip712.model.schema import EIP712SchemaField, EIP712Type
from eip712.model.types import EIP712Format
from eip712.utils import MissingRootTypeError, MultipleRootTypesError, get_primary_type
from pydantic_string_url import HttpUrl

from erc7730.common.output import ExceptionsToOutput, OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.model.context import EIP712Schema
from erc7730.model.display import (
    DateEncoding,
    FieldFormat,
)
from erc7730.model.input.context import InputDeployment, InputDomain, InputEIP712, InputEIP712Context
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import (
    InputDateParameters,
    InputDisplay,
    InputFieldDescription,
    InputFormat,
    InputNestedFields,
    InputReference,
    InputTokenAmountParameters,
)
from erc7730.model.input.metadata import InputMetadata
from erc7730.model.paths import ContainerField, ContainerPath


@final
class EIP712toERC7730Converter(ERC7730Converter[ResolvedEIP712DAppDescriptor, InputERC7730Descriptor]):
    """
    Converts Ledger legacy EIP-712 descriptor to ERC-7730 descriptor.

    Generates 1 output ERC-7730 descriptor per contract, as ERC-7730 descriptors only represent 1 contract.
    """

    @override
    def convert(
        self, descriptor: ResolvedEIP712DAppDescriptor, out: OutputAdder
    ) -> dict[str, InputERC7730Descriptor] | None:
        with ExceptionsToOutput(out):
            descriptors: dict[str, InputERC7730Descriptor] = {}

            for contract in descriptor.contracts:
                formats: dict[str, InputFormat] = {}
                schemas: list[EIP712Schema | HttpUrl] = []

                for message in contract.messages:
                    if (primary_type := self._get_primary_type(message.schema_, out)) is None:
                        return None

                    schemas.append(EIP712Schema(primaryType=primary_type, types=message.schema_))

                    formats[primary_type] = InputFormat(
                        intent=message.mapper.label,
                        fields=[self._convert_field(field) for field in message.mapper.fields],
                        required=None,
                        screens=None,
                    )

                descriptors[contract.address] = InputERC7730Descriptor(
                    context=InputEIP712Context(
                        eip712=InputEIP712(
                            domain=InputDomain(
                                name=descriptor.name,
                                version=None,
                                chainId=descriptor.chainId,
                                verifyingContract=contract.address,
                            ),
                            schemas=schemas,
                            deployments=[InputDeployment(chainId=descriptor.chainId, address=contract.address)],
                        )
                    ),
                    metadata=InputMetadata(
                        owner=contract.contractName,
                        info=None,
                        token=None,
                        constants=None,
                        enums=None,
                    ),
                    display=InputDisplay(
                        definitions=None,
                        formats=formats,
                    ),
                )

        return descriptors

    @classmethod
    def _convert_field(
        cls, field: ResolvedEIP712MapperField
    ) -> InputFieldDescription | InputReference | InputNestedFields:
        # FIXME must generate nested fields for arrays
        match field.format:
            case EIP712Format.RAW | None:
                return InputFieldDescription(path=field.path, label=field.label, format=FieldFormat.RAW, params=None)
            case EIP712Format.AMOUNT if field.assetPath is not None:
                return InputFieldDescription(
                    path=field.path,
                    label=field.label,
                    format=FieldFormat.TOKEN_AMOUNT,
                    params=InputTokenAmountParameters(tokenPath=field.assetPath),
                )
            case EIP712Format.AMOUNT:
                return InputFieldDescription(
                    path=field.path,
                    label=field.label,
                    format=FieldFormat.TOKEN_AMOUNT,
                    params=InputTokenAmountParameters(tokenPath=ContainerPath(field=ContainerField.TO)),
                )
            case EIP712Format.DATETIME:
                return InputFieldDescription(
                    path=field.path,
                    label=field.label,
                    format=FieldFormat.DATE,
                    params=InputDateParameters(encoding=DateEncoding.TIMESTAMP),
                )
            case _:
                assert_never(field.format)

    @classmethod
    def _get_primary_type(
        cls, schema: dict[EIP712Type, list[EIP712SchemaField]], out: OutputAdder
    ) -> EIP712Type | None:
        try:
            return get_primary_type(schema)
        except MissingRootTypeError:
            return out.error(
                title="Invalid EIP-712 schema",
                message="Primary type could not be determined on EIP-712 schema, as all types are referenced by"
                "other types. Please make sure your schema has a root type.",
            )
        except MultipleRootTypesError:
            return out.error(
                title="Invalid EIP-712 schema",
                message="Primary type could not be determined on EIP-712 schema, as several types are not"
                "referenced by any other type. Please make sure your schema has a single root type.",
            )
