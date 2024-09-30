from typing import final, override

from erc7730.lint.classifier import Classifier, TxClass
from erc7730.model.context import AbiJsonSchema


@final
class ABIClassifier(Classifier[AbiJsonSchema]):
    """Given an EIP712 schema, classify the transaction type with some predefined ruleset.
    (not implemented)
    """

    @override
    def classify(self, schema: AbiJsonSchema) -> TxClass | None:
        pass
