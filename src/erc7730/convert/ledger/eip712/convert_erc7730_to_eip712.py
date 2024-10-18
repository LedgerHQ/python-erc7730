from typing import assert_never, final, override

from eip712 import (
    EIP712ContractDescriptor as LegacyEIP712ContractDescriptor,
)
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
    EIP712Mapper as LegacyEIP712Mapper,
)
from eip712 import (
    EIP712MessageDescriptor as LegacyEIP712MessageDescriptor,
)

from erc7730.common.ledger import ledger_network_id
from erc7730.common.output import OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.model.context import Deployment, EIP712Field, EIP712JsonSchema
from erc7730.model.display import (
    FieldFormat,
)
from erc7730.model.paths import ContainerField, ContainerPath, DataPath
from erc7730.model.paths.path_ops import data_path_concat
from erc7730.model.resolved.context import ResolvedEIP712Context
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.display import (
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedNestedFields,
    ResolvedTokenAmountParameters,
)


@final
class ERC7730toEIP712Converter(ERC7730Converter[ResolvedERC7730Descriptor, LegacyEIP712DAppDescriptor]):
    """
    Converts ERC-7730 descriptor to Ledger legacy EIP-712 descriptor.

    Generates 1 output EIP712DAppDescriptor per chain id, as EIP-712 descriptors are chain-specific.
    """

    @override
    def convert(
        self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder
    ) -> dict[str, LegacyEIP712DAppDescriptor] | None:
        # FIXME model_construct() needs to be used here due to bad conception of EIP-712 library,
        #  which adds computed fields on validation

        context = descriptor.context
        if not isinstance(context, ResolvedEIP712Context):
            return out.error("context is not EIP712")

        if (domain := context.eip712.domain) is None or (dapp_name := domain.name) is None:
            return out.error("EIP712 domain is not defined")

        if (contract_name := descriptor.metadata.owner) is None:
            return out.error("metadata.owner is not defined")

        messages: list[LegacyEIP712MessageDescriptor] = []
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
                LegacyEIP712MessageDescriptor.model_construct(
                    schema=schema,
                    mapper=LegacyEIP712Mapper.model_construct(label=label, fields=output_fields),
                )
            )

        descriptors: dict[str, LegacyEIP712DAppDescriptor] = {}
        for deployment in context.eip712.deployments:
            output_descriptor = self._build_network_descriptor(deployment, dapp_name, contract_name, messages, out)
            if output_descriptor is not None:
                descriptors[str(deployment.chainId)] = output_descriptor
        return descriptors

    @classmethod
    def _build_network_descriptor(
        cls,
        deployment: Deployment,
        dapp_name: str,
        contract_name: str,
        messages: list[LegacyEIP712MessageDescriptor],
        out: OutputAdder,
    ) -> LegacyEIP712DAppDescriptor | None:
        if (network := ledger_network_id(deployment.chainId)) is None:
            return out.error(f"network id {deployment.chainId} not supported")

        return LegacyEIP712DAppDescriptor.model_construct(
            blockchainName=network,
            chainId=deployment.chainId,
            name=dapp_name,
            contracts=[
                LegacyEIP712ContractDescriptor.model_construct(
                    address=deployment.address.lower(), contractName=contract_name, messages=messages
                )
            ],
        )

    @classmethod
    def _get_schema(
        cls, primary_type: str, schemas: list[EIP712JsonSchema], out: OutputAdder
    ) -> dict[str, list[EIP712Field]] | None:
        for schema in schemas:
            if schema.primaryType == primary_type:
                return schema.types
        return out.error(f"schema for type {primary_type} not found")

    @classmethod
    def convert_field(
        cls, field: ResolvedField, prefix: DataPath | None, out: OutputAdder
    ) -> list[LegacyEIP712Field] | None:
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
    ) -> LegacyEIP712Field | None:
        field_path: DataPath
        asset_path: DataPath | None = None
        field_format: LegacyEIP712Format | None = None

        match field.path:
            case DataPath() as field_path:
                field_path = data_path_concat(prefix, field_path)
            case ContainerPath() as container_path:
                return out.error(f"Path {container_path} is not supported")
            case _:
                assert_never(field.path)

        match field.format:
            case None:
                field_format = None
            case FieldFormat.ADDRESS_NAME:
                field_format = LegacyEIP712Format.RAW
            case FieldFormat.RAW:
                field_format = LegacyEIP712Format.RAW
            case FieldFormat.ENUM:
                field_format = LegacyEIP712Format.RAW
            case FieldFormat.UNIT:
                field_format = LegacyEIP712Format.RAW
            case FieldFormat.DURATION:
                field_format = LegacyEIP712Format.RAW
            case FieldFormat.NFT_NAME:
                field_format = LegacyEIP712Format.RAW
            case FieldFormat.CALL_DATA:
                field_format = LegacyEIP712Format.RAW
            case FieldFormat.DATE:
                field_format = LegacyEIP712Format.DATETIME
            case FieldFormat.AMOUNT:
                field_format = LegacyEIP712Format.AMOUNT
            case FieldFormat.TOKEN_AMOUNT:
                field_format = LegacyEIP712Format.AMOUNT
                if field.params is not None and isinstance(field.params, ResolvedTokenAmountParameters):
                    match field.params.tokenPath:
                        case None:
                            pass
                        case DataPath() as token_path:
                            asset_path = data_path_concat(prefix, token_path)
                        case ContainerPath() as container_path if container_path.field == ContainerField.TO:
                            # In EIP-712 protocol, format=token with no token path => refers to verifyingContract
                            asset_path = None
                        case ContainerPath() as container_path:
                            return out.error(f"Path {container_path} is not supported")
                        case _:
                            assert_never(field.params.tokenPath)
            case _:
                assert_never(field.format)

        return LegacyEIP712Field(
            path=".".join(str(e) for e in field_path.elements),
            label=field.label,
            assetPath=asset_path,
            format=field_format,
        )
