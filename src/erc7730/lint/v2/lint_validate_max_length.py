"""
V2 linter that validates string lengths against Ledger device display limits.

Adapted from v1 ValidateMaxLengthLinter to use v2 model types.
"""

import re
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
from erc7730.lint.v2 import ERC7730Linter
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.input.v2.format import VisibilityRule
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.v2.display import (
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFieldGroup,
    ResolvedVisibilityConditions,
    ResolvedVisibilityRules,
)


@final
class ValidateMaxLengthLinter(ERC7730Linter):
    """
    Validates max length of metadata fields, display fields, and enums for Ledger device display limits.
    """

    @override
    def lint(
        self, input_descriptor: InputERC7730Descriptor, descriptor: ResolvedERC7730Descriptor, out: OutputAdder
    ) -> None:
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

        contract_name = descriptor.metadata.contractName or descriptor.context.id
        if contract_name is not None and len(contract_name) > CONTRACT_NAME_MAX_LENGTH:
            out.warning(
                title="Contract name too long",
                message=f"Contract name `{contract_name}` exceeds "
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
            if (ii := fmt.interpolatedIntent) is not None and cls._literal_length(ii) > OPERATION_TYPE_MAX_LENGTH:
                too_long_intents.add(ii)
            if fmt.id is not None and len(fmt.id) > OPERATION_TYPE_MAX_LENGTH:
                too_long_ids.add(fmt.id)

            for field in fmt.fields:
                cls._collect_long_labels(field, too_long_labels)

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

    @staticmethod
    def _is_never_displayed(visible: ResolvedVisibilityRules | None) -> bool:
        """Whether the field is only ever checked, never put on a screen.

        A ``mustMatch`` field is a constraint the device enforces without displaying it, which
        is why the descriptor may omit its label altogether. ``ifNotIn`` and ``optional`` both
        do reach a screen, so their labels still count.
        """
        if visible == VisibilityRule.NEVER:
            return True
        return isinstance(visible, ResolvedVisibilityConditions) and visible.mustMatch is not None

    _PLACEHOLDER = re.compile(r"\{[^}]*\}")

    @classmethod
    def _literal_length(cls, interpolated_intent: str) -> int:
        """Length of the text an interpolated intent is guaranteed to display.

        `{path}` is template syntax. Neither the braces nor the path inside them reaches a
        screen, and the length of the value that replaces them is not known here -- an amount
        may render as "1 ETH" or as eighteen decimal places. Only the literal text around the
        placeholders is certain to be displayed, so it is the only part that can be measured.
        Over the limit on that alone means the intent truncates whatever the values are.
        """
        return len(cls._PLACEHOLDER.sub("", interpolated_intent))

    @classmethod
    def _collect_long_labels(cls, field: ResolvedField, too_long: set[str]) -> None:
        match field:
            case ResolvedFieldDescription():
                # a label that never reaches a screen cannot be truncated on one
                if cls._is_never_displayed(field.visible):
                    return
                if field.label is not None and len(field.label) > FIELD_NAME_MAX_LENGTH:
                    too_long.add(field.label)
            case ResolvedFieldGroup():
                if field.label is not None and len(field.label) > FIELD_NAME_MAX_LENGTH:
                    too_long.add(field.label)
                for sub_field in field.fields:
                    cls._collect_long_labels(sub_field, too_long)

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
