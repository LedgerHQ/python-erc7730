import typing
from typing import assert_never, final, override

from eip712 import (
    EIP712DAppDescriptor,
    EIP712Field,
    EIP712Format,
)
from pydantic import AnyUrl

from erc7730.convert import ERC7730Converter, ToERC7730Converter
from erc7730.model.context import EIP712, Domain, EIP712Context, EIP712JsonSchema, NameType
from erc7730.model.descriptor import ERC7730Descriptor
from erc7730.model.display import (
    Display,
    Field,
    FieldDescription,
    FieldFormat,
    Format,
    TokenAmountParameters,
)
from erc7730.model.metadata import Metadata


@final
class EIP712toERC7730Converter(ToERC7730Converter[EIP712DAppDescriptor]):
    """Converts Ledger legacy EIP-712 descriptor to ERC-7730 descriptor."""

    @override
    def convert(self, descriptor: EIP712DAppDescriptor, error: ERC7730Converter.ErrorAdder) -> ERC7730Descriptor | None:
        # FIXME this code flattens all messages in first contract
        verifying_contract = None
        contract_name = descriptor.name
        if len(descriptor.contracts) > 0:
            verifying_contract = descriptor.contracts[0].address  # FIXME
            contract_name = descriptor.contracts[0].name  # FIXME
        formats = dict[str, Format]()
        schemas = list[EIP712JsonSchema | AnyUrl]()
        for contract in descriptor.contracts:
            for message in contract.messages:
                # TODO improve typing on EIP-712 library
                schema = typing.cast(dict[str, list[NameType]], message.schema_)
                mapper = message.mapper
                schemas.append(
                    EIP712JsonSchema(
                        primaryType=mapper.label,  # FIXME ?
                        types=schema,
                    )
                )
                fields = [Field(self._convert_field(field)) for field in mapper.fields]
                formats[mapper.label] = Format(
                    intent=None,  # FIXME
                    fields=fields,
                    required=None,  # FIXME
                    screens=None,
                )

        return ERC7730Descriptor(
            context=(
                EIP712Context(
                    eip712=EIP712(
                        domain=Domain(
                            name=descriptor.name,
                            version=None,  # FIXME
                            chainId=descriptor.chain_id,
                            verifyingContract=verifying_contract,
                        ),
                        schemas=schemas,
                    )
                )
            ),
            metadata=Metadata(
                owner=contract_name,
                info=None,  # FIXME
                token=None,  # FIXME
                constants=None,  # FIXME
                enums=None,  # FIXME
            ),
            display=Display(
                definitions=None,  # FIXME
                formats=formats,
            ),
        )

    @classmethod
    def _convert_field(cls, field: EIP712Field) -> FieldDescription:
        match field.format:
            case EIP712Format.AMOUNT:
                if field.assetPath is not None:
                    return FieldDescription(
                        label=field.label,
                        format=FieldFormat.TOKEN_AMOUNT,
                        params=TokenAmountParameters(tokenPath=field.assetPath),
                        path=field.path,
                    )
                else:
                    return FieldDescription(label=field.label, format=FieldFormat.AMOUNT, params=None, path=field.path)
            case EIP712Format.DATETIME:
                return FieldDescription(label=field.label, format=FieldFormat.DATE, params=None, path=field.path)
            case EIP712Format.RAW | None:
                return FieldDescription(label=field.label, format=FieldFormat.RAW, params=None, path=field.path)
            case _:
                assert_never(field.format)
