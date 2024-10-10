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
from pydantic import AnyUrl, RootModel

from erc7730.common.output import OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.model.context import Deployment, Domain, EIP712Field, EIP712JsonSchema, EIP712Type
from erc7730.model.display import (
    DateEncoding,
    DateParameters,
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
                # TODO Improve typing on EIP-712 library to use dict[EIP712Type, list[EIP712Field]]
                #  we serialize/deserialize here to be sure to have the proper types, as in some context we have dicts
                #  instead of classes.
                schema_dict = RootModel(message.schema_).model_dump()
                schema = RootModel[dict[EIP712Type, list[EIP712Field]]].model_validate(schema_dict).root

                if (primary_type := self._get_primary_type(schema, out)) is None:
                    return None

                schemas.append(EIP712JsonSchema(primaryType=primary_type, types=schema))

                formats[primary_type] = InputFormat(
                    intent=message.mapper.label,
                    fields=[self._convert_field(field) for field in message.mapper.fields],
                    required=None,
                    screens=None,
                )

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
        # FIXME must generate nested fields for arrays
        match field.format:
            case LegacyEIP712Format.RAW | None:
                return InputFieldDescription(path=field.path, label=field.label, format=FieldFormat.RAW, params=None)
            case LegacyEIP712Format.AMOUNT if field.assetPath is not None:
                return InputFieldDescription(
                    path=field.path,
                    label=field.label,
                    format=FieldFormat.TOKEN_AMOUNT,
                    params=TokenAmountParameters(tokenPath=field.assetPath),
                )
            case LegacyEIP712Format.AMOUNT:
                return InputFieldDescription(path=field.path, label=field.label, format=FieldFormat.AMOUNT, params=None)
            case LegacyEIP712Format.DATETIME:
                return InputFieldDescription(
                    path=field.path,
                    label=field.label,
                    format=FieldFormat.DATE,
                    params=DateParameters(encoding=DateEncoding.TIMESTAMP),
                )
            case _:
                assert_never(field.format)

    @classmethod
    def _get_primary_type(cls, schema: dict[EIP712Type, list[EIP712Field]], out: OutputAdder) -> EIP712Type | None:
        # TODO _schema_top_level_type() is wrong on EIP-712 library (fails with "SomeType[]" syntax)
        referenced_types = {
            field.type.rstrip("[]") for type_name, type_fields in schema.items() for field in type_fields
        }
        match len(roots := set(schema.keys()) - referenced_types - {"EIP712Domain"}):
            case 0:
                return out.error(
                    title="Invalid EIP-712 schema",
                    message="Primary type could not be determined on EIP-712 schema, as all types are referenced by"
                    "other types. Please make sure your schema has a root type.",
                )
            case 1:
                return next(iter(roots))
            case _:
                return out.error(
                    title="Invalid EIP-712 schema",
                    message="Primary type could not be determined on EIP-712 schema, as several types are not"
                    "referenced by any other type. Please make sure your schema has a single root type.",
                )
