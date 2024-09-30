from typing import final, override

from erc7730.lint.classifier import Classifier, TxClass
from erc7730.model.context import EIP712JsonSchema


@final
class EIP712Classifier(Classifier[EIP712JsonSchema]):
    """Given an EIP712 schema, classify the transaction type with some predefined ruleset.
    (implemented a basic detection of a permit)
    """

    @override
    def classify(self, schema: EIP712JsonSchema) -> TxClass | None:
        if "permit" in schema.primaryType.lower():
            return TxClass.PERMIT
        return None
