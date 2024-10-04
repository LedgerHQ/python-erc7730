import typing
from typing import assert_never, final, override

from eip712 import (
    EIP712DAppDescriptor as LegacyEIP712DAppDescriptor,
)
from eip712 import (
    EIP712Field as LegacyEIP712Field,
)
from eip712 import (
    EIP712Format as LegacyEIP712Format,
)
from eip712 import (
    EIP712MessageDescriptor as LegacyEIP712MessageDescriptor,
)
from pydantic import AnyUrl

from erc7730.common.output import OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.model.context import Deployment, Domain, EIP712Field, EIP712JsonSchema
from erc7730.model.display import (
    FieldFormat,
    TokenAmountParameters,
)
from erc7730.model.input.context import InputEIP712, InputEIP712Context
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import (
    InputDisplay,
    InputFieldDescription,
    InputFormat,
    InputNestedFields,
    InputReference,
)
from erc7730.model.metadata import Metadata


@final
class EIP712toERC7730Converter(ERC7730Converter[LegacyEIP712DAppDescriptor, InputERC7730Descriptor]):
    """
    Converts Ledger legacy EIP-712 descriptor to ERC-7730 descriptor.

    Generates 1 output ERC-7730 descriptor per contract, as ERC-7730 descriptors only represent 1 contract.
    """

    @override
    def convert(
        self, descriptor: LegacyEIP712DAppDescriptor, out: OutputAdder
    ) -> dict[str, InputERC7730Descriptor] | None:
        descriptors: dict[str, InputERC7730Descriptor] = {}

        for contract in descriptor.contracts:
            formats: dict[str, InputFormat] = {}
            schemas: list[EIP712JsonSchema | AnyUrl] = []

            for message in contract.messages:
                # TODO improve typing on EIP-712 library
                schema = typing.cast(dict[str, list[EIP712Field]], message.schema_)
                mapper = message.mapper
                # TODO make this public on EIP-712 library
                primary_type = LegacyEIP712MessageDescriptor._schema_top_level_type(schema)
                schemas.append(EIP712JsonSchema(primaryType=primary_type, types=schema))
                fields = [self._convert_field(field) for field in mapper.fields]
                formats[primary_type] = InputFormat(intent=None, fields=fields, required=None, screens=None)

            descriptors[contract.address] = InputERC7730Descriptor(
                context=InputEIP712Context(
                    eip712=InputEIP712(
                        domain=Domain(
                            name=descriptor.name,
                            version=None,
                            chainId=descriptor.chain_id,
                            verifyingContract=contract.address,
                        ),
                        schemas=schemas,
                        deployments=[Deployment(chainId=descriptor.chain_id, address=contract.address)],
                    )
                ),
                metadata=Metadata(
                    owner=contract.name,
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
    def _convert_field(cls, field: LegacyEIP712Field) -> InputFieldDescription | InputReference | InputNestedFields:
        match field.format:
            case LegacyEIP712Format.AMOUNT if field.assetPath is not None:
                return InputFieldDescription(
                    label=field.label,
                    format=FieldFormat.TOKEN_AMOUNT,
                    params=TokenAmountParameters(tokenPath=field.assetPath),
                    path=field.path,
                )
            case LegacyEIP712Format.AMOUNT:
                return InputFieldDescription(label=field.label, format=FieldFormat.AMOUNT, params=None, path=field.path)
            case LegacyEIP712Format.DATETIME:
                return InputFieldDescription(label=field.label, format=FieldFormat.DATE, params=None, path=field.path)
            case LegacyEIP712Format.RAW | None:
                return InputFieldDescription(label=field.label, format=FieldFormat.RAW, params=None, path=field.path)
            case _:
                assert_never(field.format)
