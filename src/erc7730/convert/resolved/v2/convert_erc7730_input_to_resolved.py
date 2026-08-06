"""
Converter for ERC-7730 v2 input descriptors to resolved form.

This module provides conversion from input v2 descriptors to resolved v2 descriptors.
"""

from typing import Any, assert_never, final, override

from pydantic_string_url import HttpUrl

from erc7730.common import client
from erc7730.common.abi import reduce_signature, signature_to_selector
from erc7730.common.output import ExceptionsToOutput, OutputAdder
from erc7730.convert import ERC7730Converter
from erc7730.convert.resolved.v2.constants import ConstantProvider, DefaultConstantProvider
from erc7730.convert.resolved.v2.parameters import resolve_field_parameters
from erc7730.convert.resolved.v2.references import is_field_hidden, resolve_reference
from erc7730.convert.resolved.v2.values import resolve_field_value
from erc7730.model.input.v2.common import InputMapReference
from erc7730.model.input.v2.context import (
    InputContract,
    InputContractContext,
    InputDeployment,
    InputDomain,
    InputEIP712,
    InputEIP712Context,
    InputFactory,
)
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.input.v2.display import (
    InputDisplay,
    InputField,
    InputFieldDefinition,
    InputFieldDescription,
    InputFieldGroup,
    InputFormat,
    InputReference,
)
from erc7730.model.input.v2.format import FieldFormat
from erc7730.model.input.v2.metadata import InputMetadata
from erc7730.model.paths import (
    ROOT_DATA_PATH,
    Array,
    ArrayElement,
    ArraySlice,
    ContainerPath,
    DataPath,
    DescriptorPath,
    Field,
)
from erc7730.model.paths.path_ops import data_path_concat
from erc7730.model.resolved.display import ResolvedValueConstant, ResolvedValuePath
from erc7730.model.resolved.metadata import EnumDefinition
from erc7730.model.resolved.v2.context import (
    ResolvedContract,
    ResolvedContractContext,
    ResolvedDeployment,
    ResolvedDomain,
    ResolvedEIP712,
    ResolvedEIP712Context,
    ResolvedFactory,
)
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.v2.display import (
    ResolvedDisplay,
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFieldGroup,
    ResolvedFormat,
)
from erc7730.model.resolved.v2.metadata import ResolvedMapDefinition, ResolvedMetadata, ResolvedOwnerInfo
from erc7730.model.types import Address, Id, Selector


@final
class ERC7730InputToResolved(ERC7730Converter[InputERC7730Descriptor, ResolvedERC7730Descriptor]):
    """
    Converts ERC-7730 v2 descriptor input to resolved form.

    After conversion, the descriptor is in resolved form:
     - URLs have been fetched (deprecated ABI and schemas fields are ignored)
     - Contract addresses have been normalized to lowercase
     - References have been inlined
     - Constants have been inlined
     - Field definitions have been inlined
     - Field groups have been processed
     - Selectors have been converted to 4 bytes form
     - Maps have been resolved
    """

    @override
    def convert(
        self, descriptor: InputERC7730Descriptor, out: OutputAdder, *, strict_maps: bool = False
    ) -> ResolvedERC7730Descriptor | None:
        with ExceptionsToOutput(out):
            constants = DefaultConstantProvider(descriptor)

            if (context := self._resolve_context(descriptor.context, constants, out, strict_maps=strict_maps)) is None:
                return None
            if (
                metadata := self._resolve_metadata(descriptor.metadata, constants, out, strict_maps=strict_maps)
            ) is None:
                return None
            if (
                display := self._resolve_display(
                    descriptor.display, context, metadata.enums, constants, out, strict_maps=strict_maps
                )
            ) is None:
                return None

            return ResolvedERC7730Descriptor.model_validate(
                {
                    "$schema": descriptor.schema_,
                    "$comment": descriptor.comment,
                    "context": context,
                    "metadata": metadata,
                    "display": display,
                }
            )

        # noinspection PyUnreachableCode
        return None

    @classmethod
    def _resolve_context(
        cls,
        context: InputContractContext | InputEIP712Context,
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> ResolvedContractContext | ResolvedEIP712Context | None:
        match context:
            case InputContractContext():
                return cls._resolve_context_contract(context, out)
            case InputEIP712Context():
                return cls._resolve_context_eip712(context, constants, out, strict_maps=strict_maps)
            case _:
                assert_never(context)

    @classmethod
    def _resolve_metadata(
        cls,
        metadata: InputMetadata,
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> ResolvedMetadata | None:
        resolved_enums = {}
        if metadata.enums is not None:
            for enum_id, enum in metadata.enums.items():
                if (resolved_enum := cls._resolve_enum(enum, out)) is not None:
                    resolved_enums[enum_id] = resolved_enum

        resolved_maps = {}
        if metadata.maps is not None:
            for map_id, map_def in metadata.maps.items():
                resolved_maps[map_id] = ResolvedMapDefinition.model_validate(
                    {"$keyType": map_def.keyType, "values": map_def.values}
                )

        resolved_info = None
        if metadata.info is not None:
            resolved_info = ResolvedOwnerInfo(
                legalName=metadata.info.legalName,
                lastUpdate=metadata.info.lastUpdate,
                deploymentDate=metadata.info.deploymentDate,
                url=metadata.info.url,
            )

        resolved_owner = cls._resolve_string_or_map(
            metadata.owner, "owner", constants, out, strict_maps=strict_maps, allow_data_path_in_key=False
        )
        if strict_maps and isinstance(metadata.owner, InputMapReference):
            return None
        resolved_contract_name = cls._resolve_string_or_map(
            metadata.contractName, "contractName", constants, out, strict_maps=strict_maps, allow_data_path_in_key=False
        )
        if strict_maps and isinstance(metadata.contractName, InputMapReference):
            return None

        return ResolvedMetadata(
            owner=resolved_owner,
            contractName=resolved_contract_name,
            info=resolved_info,
            token=metadata.token,
            constants=metadata.constants,
            enums=resolved_enums or None,
            maps=resolved_maps or None,
        )

    @classmethod
    def _resolve_enum(cls, enum: HttpUrl | EnumDefinition, out: OutputAdder) -> dict[str, str] | None:
        match enum:
            case HttpUrl() as url:
                try:
                    return client.get(url=url, model=EnumDefinition)
                except Exception as e:
                    return out.error(
                        title="Failed to fetch enum definition from URL",
                        message=f'Failed to fetch enum definition from URL "{url}": {e}',
                    )
            case dict():
                return enum
            case _:
                assert_never(enum)

    @classmethod
    def _resolve_string_or_map(
        cls,
        value: DescriptorPath | str | InputMapReference | None,
        field_name: str,
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
        allow_data_path_in_key: bool = True,
    ) -> str | None:
        """Resolve a string field that may be a literal, a constant reference, or a map reference.

        :param allow_data_path_in_key: if False, reject structured data paths (#.) in the map keyPath.
            Should be False for fields in the context and metadata sections where data paths have no meaning.
        """
        if value is None:
            return None
        if isinstance(value, InputMapReference):
            if not allow_data_path_in_key and isinstance(value.keyPath, DataPath):
                out.error(
                    title="Invalid map keyPath",
                    message=f"Map reference for {field_name} uses a structured data path "
                    f'"{value.keyPath}" as keyPath, but structured data paths are not valid in '
                    "context/metadata sections. Use a container path (@.) or descriptor path ($.) instead.",
                )
            constants.resolve_map_reference(ROOT_DATA_PATH, value, out)
            if strict_maps:
                out.error(
                    title="Unsupported map reference",
                    message=f"Map references are not yet supported for {field_name}. Map at {value.map} with "
                    f"keyPath {value.keyPath} cannot be resolved.",
                )
            return None
        resolved = constants.resolve(value, out)
        return str(resolved) if resolved is not None else None

    @classmethod
    def _resolve_context_contract(
        cls, context: InputContractContext, out: OutputAdder
    ) -> ResolvedContractContext | None:
        if (contract := cls._resolve_contract(context.contract, out)) is None:
            return None

        return ResolvedContractContext.model_validate({"$id": context.id, "contract": contract})

    @classmethod
    def _resolve_contract(cls, contract: InputContract, out: OutputAdder) -> ResolvedContract | None:
        # Note: In v2, ABI field is deprecated and ignored during resolution
        if (deployments := cls._resolve_deployments(contract.deployments, out)) is None:
            return None

        if contract.factory is None:
            factory = None
        elif (factory := cls._resolve_factory(contract.factory, out)) is None:
            return None

        return ResolvedContract(
            deployments=deployments,
            addressMatcher=str(contract.addressMatcher) if contract.addressMatcher is not None else None,
            factory=factory,
        )

    @classmethod
    def _resolve_deployments(
        cls, deployments: list[InputDeployment], out: OutputAdder
    ) -> list[ResolvedDeployment] | None:
        resolved_deployments = []
        for deployment in deployments:
            if (resolved_deployment := cls._resolve_deployment(deployment, out)) is not None:
                resolved_deployments.append(resolved_deployment)
        return resolved_deployments

    @classmethod
    def _resolve_deployment(cls, deployment: InputDeployment, out: OutputAdder) -> ResolvedDeployment | None:
        return ResolvedDeployment(chainId=deployment.chainId, address=Address(deployment.address))

    @classmethod
    def _resolve_factory(cls, factory: InputFactory, out: OutputAdder) -> ResolvedFactory | None:
        if (deployments := cls._resolve_deployments(factory.deployments, out)) is None:
            return None

        return ResolvedFactory(deployments=deployments, deployEvent=factory.deployEvent)

    @classmethod
    def _resolve_context_eip712(
        cls,
        context: InputEIP712Context,
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> ResolvedEIP712Context | None:
        if (eip712 := cls._resolve_eip712(context.eip712, constants, out, strict_maps=strict_maps)) is None:
            return None

        return ResolvedEIP712Context.model_validate({"$id": context.id, "eip712": eip712})

    @classmethod
    def _resolve_eip712(
        cls,
        eip712: InputEIP712,
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> ResolvedEIP712 | None:
        if eip712.domain is None:
            domain = None
        elif (domain := cls._resolve_domain(eip712.domain, constants, out, strict_maps=strict_maps)) is None:
            return None

        # Note: In v2, schemas field is deprecated and ignored during resolution
        if (deployments := cls._resolve_deployments(eip712.deployments, out)) is None:
            return None

        return ResolvedEIP712(
            domain=domain,
            domainSeparator=eip712.domainSeparator,
            deployments=deployments,
        )

    @classmethod
    def _resolve_domain(
        cls,
        domain: InputDomain,
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> ResolvedDomain | None:
        resolved_name = cls._resolve_string_or_map(
            domain.name, "domain.name", constants, out, strict_maps=strict_maps, allow_data_path_in_key=False
        )
        if strict_maps and isinstance(domain.name, InputMapReference):
            return None
        resolved_version = cls._resolve_string_or_map(
            domain.version, "domain.version", constants, out, strict_maps=strict_maps, allow_data_path_in_key=False
        )
        if strict_maps and isinstance(domain.version, InputMapReference):
            return None

        return ResolvedDomain(
            name=resolved_name,
            version=resolved_version,
            chainId=domain.chainId,
            verifyingContract=None if domain.verifyingContract is None else Address(domain.verifyingContract),
            salt=domain.salt,
        )

    @classmethod
    def _resolve_display(
        cls,
        display: InputDisplay,
        context: ResolvedContractContext | ResolvedEIP712Context,
        enums: dict[Id, EnumDefinition] | None,
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> ResolvedDisplay | None:
        definitions = display.definitions or {}
        enums = enums or {}
        formats = {}
        for format_id, format in display.formats.items():
            if (resolved_format_id := cls._resolve_format_id(format_id, context, out)) is None:
                return None
            if (
                resolved_format := cls._resolve_format(
                    format, definitions, enums, constants, out, strict_maps=strict_maps
                )
            ) is None:
                return None
            if resolved_format_id in formats:
                return out.error(
                    title="Duplicate format",
                    message=f"Descriptor contains 2 formats sections for {resolved_format_id}",
                )
            formats[resolved_format_id] = resolved_format

        return ResolvedDisplay(definitions=None, formats=formats)

    @classmethod
    def _resolve_field_description(
        cls,
        prefix: DataPath,
        definition: InputFieldDescription,
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> ResolvedFieldDescription | None:
        match definition.format:
            case None | FieldFormat.RAW | FieldFormat.AMOUNT | FieldFormat.TOKEN_AMOUNT | FieldFormat.DURATION:
                pass
            case (
                FieldFormat.ADDRESS_NAME
                | FieldFormat.INTEROPERABLE_ADDRESS_NAME
                | FieldFormat.TOKEN_TICKER
                | FieldFormat.CALL_DATA
                | FieldFormat.NFT_NAME
                | FieldFormat.DATE
                | FieldFormat.UNIT
                | FieldFormat.ENUM
            ):
                if definition.params is None:
                    return out.error(
                        title="Missing parameters",
                        message=f"""Field format "{definition.format.value}" requires parameters to be defined, """
                        f"""they are missing for field "{definition.path}".""",
                    )
            case FieldFormat.CHAIN_ID:
                pass
            case _:
                assert_never(definition.format)

        params = resolve_field_parameters(prefix, definition.params, enums, constants, out, strict_maps=strict_maps)

        if (
            value_or_path := resolve_field_value(
                prefix, definition, definition.format, constants, out, strict_maps=strict_maps
            )
        ) is None:
            return None

        # Convert InputEncryptionParameters to ResolvedEncryptionParameters if present
        resolved_encryption = None
        if definition.encryption is not None:
            from erc7730.model.resolved.v2.display import ResolvedEncryptionParameters

            resolved_encryption = ResolvedEncryptionParameters(
                scheme=definition.encryption.scheme,
                plaintextType=definition.encryption.plaintextType,
                fallbackLabel=definition.encryption.fallbackLabel,
            )

        # Convert InputVisibilityConditions to resolved dict for discriminator compatibility
        resolved_visible: str | dict[str, Any] | None
        if definition.visible is not None and not isinstance(definition.visible, str):
            from erc7730.model.input.v2.display import InputVisibilityConditions

            if isinstance(definition.visible, InputVisibilityConditions):
                visibility_dict: dict[str, Any] = {}
                if definition.visible.ifNotIn is not None:
                    visibility_dict["ifNotIn"] = definition.visible.ifNotIn
                if definition.visible.mustBe is not None:
                    visibility_dict["mustBe"] = definition.visible.mustBe
                resolved_visible = visibility_dict
            else:
                resolved_visible = None
        else:
            resolved_visible = definition.visible

        resolved_label: str | None = None
        if definition.label is not None:
            if isinstance(definition.label, InputMapReference):
                constants.resolve_map_reference(prefix, definition.label, out)
                if strict_maps:
                    return out.error(
                        title="Unsupported map reference",
                        message=f"Map references are not yet supported for label. Map at {definition.label.map} "
                        f"with keyPath {definition.label.keyPath} cannot be resolved.",
                    )
            else:
                resolved_label = constants.resolve(definition.label, out)

        if (
            resolved_label is None
            and not is_field_hidden(resolved_visible)
            and (definition.label is None or not isinstance(definition.label, InputMapReference))
        ):
            return out.error(
                title="Missing display field label",
                message=f'Label must be defined on the display field for path "{definition.path}".',
            )

        params_dict = params.model_dump(by_alias=True, exclude_none=True) if params is not None else None
        if params_dict is not None and not params_dict:
            params_dict = None
        encryption_dict = (
            resolved_encryption.model_dump(by_alias=True, exclude_none=True)
            if resolved_encryption is not None
            else None
        )

        field_dict: dict[str, Any] = {
            "$id": definition.id,
            "visible": resolved_visible,
            "label": resolved_label,
            "format": FieldFormat(definition.format) if definition.format is not None else None,
            "params": params_dict,
            "separator": definition.separator,
            "encryption": encryption_dict,
        }

        # Set either path or value based on the ResolvedValue type
        if isinstance(value_or_path, ResolvedValuePath):
            field_dict["path"] = str(value_or_path.path)
            field_dict["value"] = None
        elif isinstance(value_or_path, ResolvedValueConstant):
            field_dict["path"] = None
            field_dict["value"] = value_or_path.value
        else:
            return out.error(
                title="Invalid value type",
                message=f"Unexpected value type: {type(value_or_path)}",
            )

        return ResolvedFieldDescription.model_validate(field_dict)

    @classmethod
    def _resolve_format_id(
        cls,
        format_id: str,
        context: ResolvedContractContext | ResolvedEIP712Context,
        out: OutputAdder,
    ) -> str | Selector | None:
        match context:
            case ResolvedContractContext():
                if format_id.startswith("0x"):
                    return Selector(format_id)

                if (reduced_signature := reduce_signature(format_id)) is not None:
                    return Selector(signature_to_selector(reduced_signature))

                return out.error(
                    title="Invalid selector",
                    message=f""""{format_id}" is not a valid function signature or selector.""",
                )
            case ResolvedEIP712Context():
                return format_id
            case _:
                assert_never(context)

    @classmethod
    def _resolve_format(
        cls,
        format: InputFormat,
        definitions: dict[Id, InputFieldDefinition],
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> ResolvedFormat | None:
        if (
            fields := cls._resolve_fields(
                ROOT_DATA_PATH, format.fields, definitions, enums, constants, out, strict_maps=strict_maps
            )
        ) is None:
            return None

        resolved_interpolated_intent = cls._resolve_string_or_map(
            format.interpolatedIntent, "interpolatedIntent", constants, out, strict_maps=strict_maps
        )
        if strict_maps and isinstance(format.interpolatedIntent, InputMapReference):
            return None

        return ResolvedFormat.model_validate(
            {
                "$id": format.id,
                "intent": format.intent,
                "interpolatedIntent": resolved_interpolated_intent,
                "fields": [f.model_dump(by_alias=True, exclude_none=True) for f in fields],
            }
        )

    @classmethod
    def _resolve_fields(
        cls,
        prefix: DataPath,
        fields: list[InputField],
        definitions: dict[Id, InputFieldDefinition],
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> list[ResolvedField] | None:
        resolved_fields = []
        for input_format in fields:
            if (
                resolved_field := cls._resolve_field(
                    prefix, input_format, definitions, enums, constants, out, strict_maps=strict_maps
                )
            ) is None:
                return None
            resolved_fields.extend(resolved_field)
        return resolved_fields

    @classmethod
    def _resolve_field(
        cls,
        prefix: DataPath,
        field: InputField,
        definitions: dict[Id, InputFieldDefinition],
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> list[ResolvedField] | None:
        resolved_fields: list[ResolvedField] = []
        match field:
            case InputReference():
                if (
                    resolved_field := resolve_reference(
                        prefix, field, definitions, enums, constants, out, strict_maps=strict_maps
                    )
                ) is None:
                    return None
                resolved_fields.append(resolved_field)
            case InputFieldDescription():
                if (
                    resolved_field := cls._resolve_field_description(
                        prefix, field, enums, constants, out, strict_maps=strict_maps
                    )
                ) is None:
                    return None
                resolved_fields.append(resolved_field)
            case InputFieldGroup():
                if (
                    resolved_field_group := cls._resolve_field_group(
                        prefix, field, definitions, enums, constants, out, strict_maps=strict_maps
                    )
                ) is None:
                    return None
                resolved_fields.extend(resolved_field_group)
            case _:
                assert_never(field)
        return resolved_fields

    @classmethod
    def _resolve_field_group(
        cls,
        prefix: DataPath,
        group: InputFieldGroup,
        definitions: dict[Id, InputFieldDefinition],
        enums: dict[Id, EnumDefinition],
        constants: ConstantProvider,
        out: OutputAdder,
        *,
        strict_maps: bool = False,
    ) -> list[ResolvedFieldGroup | ResolvedFieldDescription] | None:
        if group.path is None:
            if (
                resolved_fields := cls._resolve_fields(
                    prefix=prefix,
                    fields=group.fields,
                    definitions=definitions,
                    enums=enums,
                    constants=constants,
                    out=out,
                    strict_maps=strict_maps,
                )
            ) is None:
                return None
            return [
                ResolvedFieldGroup.model_validate(
                    {
                        "$id": group.id,
                        "label": group.label,
                        "iteration": group.iteration,
                        "fields": [f.model_dump(by_alias=True, exclude_none=True) for f in resolved_fields],
                    }
                )
            ]

        path: DataPath
        match constants.resolve_path(group.path, out):
            case None:
                return None
            case DataPath() as data_path:
                path = data_path_concat(prefix, data_path)
            case ContainerPath() as container_path:
                return out.error(
                    title="Invalid path type",
                    message=f"Container path {container_path} cannot be used with field groups.",
                )
            case _:
                assert_never(group.path)

        if (
            resolved_fields := cls._resolve_fields(
                prefix=path,
                fields=group.fields,
                definitions=definitions,
                enums=enums,
                constants=constants,
                out=out,
                strict_maps=strict_maps,
            )
        ) is None:
            return None

        match path.elements[-1]:
            case Field() | ArrayElement():
                return resolved_fields
            case ArraySlice():
                return out.error(
                    title="Invalid field group",
                    message="Using field groups on an array slice is not allowed.",
                )
            case Array():
                return [
                    ResolvedFieldGroup.model_validate(
                        {
                            "$id": group.id,
                            "path": str(path),
                            "label": group.label,
                            "iteration": group.iteration,
                            "fields": [f.model_dump(by_alias=True, exclude_none=True) for f in resolved_fields],
                        }
                    )
                ]
            case _:
                assert_never(path.elements[-1])
