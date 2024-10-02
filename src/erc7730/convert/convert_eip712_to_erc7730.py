import typing
from typing import assert_never, final, override

from eip712 import (
    EIP712DAppDescriptor,
    EIP712Field,
    EIP712Format,
)
from pydantic import AnyUrl

from erc7730.convert import ERC7730Converter
from erc7730.model.context import Deployment, Domain, EIP712JsonSchema, NameType
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
from erc7730.model.types import ContractAddress


@final
class EIP712toERC7730Converter(ERC7730Converter[EIP712DAppDescriptor, InputERC7730Descriptor]):
    """Converts Ledger legacy EIP-712 descriptor to ERC-7730 descriptor."""

    @override
    def convert(
        self, descriptor: EIP712DAppDescriptor, error: ERC7730Converter.ErrorAdder
    ) -> InputERC7730Descriptor | None:
        # FIXME this code flattens all messages in first contract.
        #  converter must be changed to output a list[InputERC7730Descriptor]
        #  1 output InputERC7730Descriptor per input contract

        verifying_contract: ContractAddress | None = None
        contract_name = descriptor.name
        if len(descriptor.contracts) > 0:
            verifying_contract = descriptor.contracts[0].address  # FIXME
            contract_name = descriptor.contracts[0].name  # FIXME

        if verifying_contract is None:
            return error.error("verifying_contract is undefined")

        formats = dict[str, InputFormat]()
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
                fields = [self._convert_field(field) for field in mapper.fields]
                formats[mapper.label] = InputFormat(
                    intent=None,  # FIXME
                    fields=fields,
                    required=None,  # FIXME
                    screens=None,
                )

        return InputERC7730Descriptor(
            context=InputEIP712Context(
                eip712=InputEIP712(
                    domain=Domain(
                        name=descriptor.name,
                        version=None,  # FIXME
                        chainId=descriptor.chain_id,
                        verifyingContract=verifying_contract,
                    ),
                    schemas=schemas,
                    deployments=[Deployment(chainId=descriptor.chain_id, address=verifying_contract)],
                )
            ),
            metadata=Metadata(
                owner=contract_name,
                info=None,  # FIXME
                token=None,  # FIXME
                constants=None,  # FIXME
                enums=None,  # FIXME
            ),
            display=InputDisplay(
                definitions=None,  # FIXME
                formats=formats,
            ),
        )

    @classmethod
    def _convert_field(cls, field: EIP712Field) -> InputFieldDescription | InputReference | InputNestedFields:
        match field.format:
            case EIP712Format.AMOUNT if field.assetPath is not None:
                return InputFieldDescription(
                    label=field.label,
                    format=FieldFormat.TOKEN_AMOUNT,
                    params=TokenAmountParameters(tokenPath=field.assetPath),
                    path=field.path,
                )
            case EIP712Format.AMOUNT:
                return InputFieldDescription(label=field.label, format=FieldFormat.AMOUNT, params=None, path=field.path)
            case EIP712Format.DATETIME:
                return InputFieldDescription(label=field.label, format=FieldFormat.DATE, params=None, path=field.path)
            case EIP712Format.RAW | None:
                return InputFieldDescription(label=field.label, format=FieldFormat.RAW, params=None, path=field.path)
            case _:
                assert_never(field.format)
