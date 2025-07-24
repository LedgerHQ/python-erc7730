from typing import final, override

from erc7730.common.ledger import (
    CONTRACT_NAME_MAX_LENGTH,
    CREATOR_LEGAL_NAME_MAX_LENGTH,
    CREATOR_NAME_MAX_LENGTH,
    CREATOR_URL_MAX_LENGTH,
    ENUM_MAX_LENGTH,
    FIELD_NAME_MAX_LENGTH,
    OPERATION_TYPE_MAX_LENGTH,
)
from erc7730.common.output import OutputAdder
from erc7730.lint import ERC7730Linter
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.display import ResolvedFieldDescription, ResolvedNestedFields


@final
class ValidateMaxLengthLinter(ERC7730Linter):
    """
    - validate max length of metadata fields
    - validate max length of display fields
    - validate max length of enums
    """

    @override
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        self._validate_metadata_lengths(descriptor, out)
        self._validate_display_lengths(descriptor, out)
        self._validate_enum_lengths(descriptor, out)

    @classmethod
    def _validate_metadata_lengths(cls, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        if descriptor.metadata.owner is not None and len(descriptor.metadata.owner) > CREATOR_NAME_MAX_LENGTH:
            out.warning(
                title="Owner too long",
                message=f"Owner `{descriptor.metadata.owner}` exceeds {CREATOR_NAME_MAX_LENGTH}"
                " characters and may be truncated on Ledger devices.",
            )

        if descriptor.metadata.info is not None:
            if (
                descriptor.metadata.info.legalName is not None
                and len(descriptor.metadata.info.legalName) > CREATOR_LEGAL_NAME_MAX_LENGTH
            ):
                out.warning(
                    title="Legal name too long",
                    message=f"Legal name `{descriptor.metadata.info.legalName}` exceeds "
                    f"{CREATOR_LEGAL_NAME_MAX_LENGTH} characters and may be truncated on Ledger devices.",
                )
            if descriptor.metadata.info.url is not None and len(descriptor.metadata.info.url) > CREATOR_URL_MAX_LENGTH:
                out.warning(
                    title="URL too long",
                    message=f"URL `{descriptor.metadata.info.url}` exceeds "
                    f"{CREATOR_URL_MAX_LENGTH} characters and may be truncated on Ledger devices.",
                )

        if descriptor.context.id is not None and len(descriptor.context.id) > CONTRACT_NAME_MAX_LENGTH:
            out.warning(
                title="Contract id too long",
                message=f"Contract id `{descriptor.context.id}` exceeds "
                f"{CONTRACT_NAME_MAX_LENGTH} characters and may be truncated on Ledger devices.",
            )

    @classmethod
    def _validate_display_lengths(cls, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        too_long_intents: set[str] = set()
        too_long_ids: set[str] = set()
        too_long_labels: set[str] = set()
        for fmt in descriptor.display.formats.values():
            if fmt.intent is not None and isinstance(fmt.intent, str) and len(fmt.intent) > OPERATION_TYPE_MAX_LENGTH:
                too_long_intents.add(fmt.intent)
            if fmt.id is not None and len(fmt.id) > OPERATION_TYPE_MAX_LENGTH:
                too_long_ids.add(fmt.id)

            for field in fmt.fields:
                match field:
                    case ResolvedFieldDescription():
                        if len(field.label) > FIELD_NAME_MAX_LENGTH:
                            too_long_labels.add(f"{field.label}")
                    case ResolvedNestedFields():
                        for nested_field in field.fields:
                            if len(nested_field.label) > FIELD_NAME_MAX_LENGTH:
                                too_long_labels.add(f"{nested_field.label}")

        if too_long_intents:
            out.warning(
                title="Display intent too long",
                message=f"Display intent(s) `{', '.join(too_long_intents)}` exceed "
                f"{OPERATION_TYPE_MAX_LENGTH} characters and may be truncated on Ledger devices.",
            )
        if too_long_ids:
            out.warning(
                title="Display id too long",
                message=f"Display id(s) `{', '.join(too_long_ids)}` exceed "
                f"{OPERATION_TYPE_MAX_LENGTH} characters and may be truncated on Ledger devices.",
            )
        if too_long_labels:
            out.warning(
                title="Display label too long",
                message=f"Display label(s) `{', '.join(too_long_labels)}` exceed "
                f"{FIELD_NAME_MAX_LENGTH} characters and may be truncated on Ledger devices.",
            )

    @classmethod
    def _validate_enum_lengths(cls, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        too_long_enums: set[str] = set()
        if descriptor.metadata.enums is not None:
            for enum in descriptor.metadata.enums.values():
                for enum_entry in enum.values():
                    if len(enum_entry) > ENUM_MAX_LENGTH:
                        too_long_enums.add(enum_entry)

        if too_long_enums:
            out.warning(
                title="Enum entry too long",
                message=f"Enum entry(s) `{', '.join(too_long_enums)}` exceed "
                f"{ENUM_MAX_LENGTH} characters and may be truncated on Ledger devices.",
            )
