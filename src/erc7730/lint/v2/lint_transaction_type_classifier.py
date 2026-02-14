"""
V2 linter that classifies transaction types and validates expected display fields.

In v2, classification relies on:
  - For EIP-712 context: the format key (primaryType) — e.g., "Permit*" → PERMIT
  - For contract context: the fetched Etherscan ABI (via ABIClassifier, currently unimplemented)
"""

from typing import final, override

from erc7730.common import client
from erc7730.common.output import OutputAdder
from erc7730.lint.classifier import TxClass
from erc7730.lint.classifier.abi_classifier import ABIClassifier
from erc7730.lint.v2 import ERC7730Linter
from erc7730.model.resolved.v2.context import ResolvedContractContext, ResolvedEIP712Context
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.v2.display import ResolvedDisplay, ResolvedField, ResolvedFieldDescription, ResolvedFormat


@final
class ClassifyTransactionTypeLinter(ERC7730Linter):
    """
    Classifies transaction type from context/format and validates expected display fields.

    For EIP-712: classifies by format key (primaryType). If "permit" found in format key, classifies as PERMIT.
    For contract: classifies from fetched Etherscan ABI using ABIClassifier.
    """

    @override
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        if (tx_class := self._determine_tx_class(descriptor)) is None:
            return None
        DisplayFormatChecker(tx_class, descriptor.display).check(out)

    @classmethod
    def _determine_tx_class(cls, descriptor: ResolvedERC7730Descriptor) -> TxClass | None:
        match descriptor.context:
            case ResolvedEIP712Context():
                # In v2, no schemas — classify from format keys (primaryType)
                for format_key in descriptor.display.formats:
                    if "permit" in format_key.lower():
                        return TxClass.PERMIT
                return None
            case ResolvedContractContext():
                # Try to classify from fetched ABI
                return cls._classify_from_fetched_abi(descriptor.context)

    @classmethod
    def _classify_from_fetched_abi(cls, context: ResolvedContractContext) -> TxClass | None:
        if (deployments := context.contract.deployments) is None:
            return None
        for deployment in deployments:
            try:
                if (abis := client.get_contract_abis(deployment.chainId, deployment.address)) is not None:
                    return ABIClassifier().classify(list(abis))
            except Exception:  # nosec B112 - intentional: try next deployment on failure
                continue
        return None


class DisplayFormatChecker:
    """Given a transaction class and v2 display formats, check if all the required fields of a given
    transaction class are being displayed.
    """

    def __init__(self, tx_class: TxClass, display: ResolvedDisplay):
        self.tx_class = tx_class
        self.display = display

    def check(self, out: OutputAdder) -> None:
        match self.tx_class:
            case TxClass.PERMIT:
                fields = self._get_all_displayed_fields(self.display.formats)
                if not self._fields_contain("spender", fields):
                    out.warning(
                        title="Expected display field missing",
                        message="Contract detected as Permit but no spender field displayed",
                    )
                if not self._fields_contain("amount", fields):
                    out.warning(
                        title="Expected display field missing",
                        message="Contract detected as Permit but no amount field displayed",
                    )
                if (
                    not self._fields_contain("valid until", fields)
                    and not self._fields_contain("expiry", fields)
                    and not self._fields_contain("expiration", fields)
                    and not self._fields_contain("deadline", fields)
                ):
                    out.warning(
                        title="Expected display field missing",
                        message="Contract detected as Permit but no expiration field displayed",
                    )
            case _:
                pass

    @classmethod
    def _get_all_displayed_fields(cls, formats: dict[str, ResolvedFormat]) -> set[str]:
        fields: set[str] = set()
        for fmt in formats.values():
            for field in fmt.fields:
                cls._collect_field_labels(field, fields)
        return fields

    @classmethod
    def _collect_field_labels(cls, field: ResolvedField, labels: set[str]) -> None:
        match field:
            case ResolvedFieldDescription():
                labels.add(field.label)
            case _:
                # ResolvedFieldGroup — recurse into sub-fields
                if hasattr(field, "fields"):
                    for sub_field in field.fields:
                        cls._collect_field_labels(sub_field, labels)

    @classmethod
    def _fields_contain(cls, word: str, fields: set[str]) -> bool:
        """Check if the provided keyword is contained in one of the fields (case insensitive)."""
        return any(word.lower() in field.lower() for field in fields)
