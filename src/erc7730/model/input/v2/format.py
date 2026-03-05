"""
Object model for ERC-7730 v2 descriptors `display` section enums and format types.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v2.schema.json
"""

from enum import StrEnum

from erc7730.model.display import DateEncoding as BaseDataEncoding


class FieldFormat(StrEnum):
    """
    The format of the field (v2), that will be used to format the field value in a human readable way.
    """

    RAW = "raw"
    """The field should be displayed as the natural representation of the underlying structured data type."""

    ADDRESS_NAME = "addressName"
    """The field should be displayed as a trusted name, or as a raw address if no names are found in trusted sources.
    List of trusted sources can be optionally specified in parameters."""

    INTEROPERABLE_ADDRESS_NAME = "interoperableAddressName"
    """The field should be displayed as a trusted name using interoperable address name resolution."""

    TOKEN_TICKER = "tokenTicker"  # nosec B105 - constant string, not credentials
    """The field should be displayed as an ERC 20 token ticker.
    If no token definitions are found, fall back to the raw address."""

    CALL_DATA = "calldata"
    """The field is itself a calldata embedded in main call. Another ERC 7730 should be used to parse this field. If not
    available or not supported, the wallet MAY display a hash of the embedded calldata instead."""

    AMOUNT = "amount"
    """The field should be displayed as an amount in underlying currency, converted using the best magnitude / ticker
    available."""

    TOKEN_AMOUNT = "tokenAmount"  # nosec B105 - bandit false positive
    """The field should be displayed as an amount, preceded by the ticker. The magnitude and ticker should be derived
    from the tokenPath parameter corresponding metadata."""

    NFT_NAME = "nftName"
    """The field should be displayed as a single NFT names, or as a raw token Id if a specific name is not found.
    Collection is specified by the collectionPath parameter."""

    DATE = "date"
    """The field should be displayed as a date. Suggested RFC3339 representation. Parameter specifies the encoding of
    the date."""

    DURATION = "duration"
    """The field should be displayed as a duration in HH:MM:ss form. Value is interpreted as a number of seconds."""

    UNIT = "unit"
    """The field should be displayed as a percentage. Magnitude of the percentage encoding is specified as a parameter.
    Example: a value of 3000 with magnitude 4 is displayed as 0.3%."""

    ENUM = "enum"
    """The field should be displayed as a human readable string by converting the value using the enum referenced in
    parameters."""

    CHAIN_ID = "chainId"
    """The field should be displayed as a Blockchain explicit name, as defined in EIP-155.
    The name is resolved based on the chain id value."""


# Re-export base enums that haven't changed
DateEncoding = BaseDataEncoding
