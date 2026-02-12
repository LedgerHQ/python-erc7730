"""
Object model for ERC-7730 v2 discriminated unions and discriminator functions.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v2.schema.json
"""

from typing import Any

from erc7730.common.properties import has_any_property


def field_discriminator(v: Any) -> str | None:
    """
    Discriminator function for the Field union type (v2).

    :param v: deserialized raw data
    :return: the discriminator tag
    """
    if has_any_property(v, "$ref"):
        return "reference"
    if has_any_property(v, "fields"):
        return "field_group"  # was "nested_fields" in v1
    if has_any_property(v, "label", "format"):
        return "field_description"
    return None


def field_parameters_discriminator(v: Any) -> str | None:
    """
    Discriminator function for the FieldParameters union type (v2).

    Note: addressName and interoperableAddressName parameters have identical schemas and cannot be
    reliably distinguished by data shape alone. The correct type is determined by the parent field's
    format property. For deserialization, ambiguous cases default to address_name. The converter
    correctly routes parameters based on the format context.

    :param v: deserialized raw data
    :return: the discriminator tag
    """
    if has_any_property(v, "tokenPath", "token", "nativeCurrencyAddress", "threshold", "message"):
        return "token_amount"
    if has_any_property(v, "encoding"):
        return "date"
    if has_any_property(v, "collectionPath", "collection"):
        return "nft_name"
    if has_any_property(v, "base"):
        return "unit"
    if has_any_property(v, "$ref", "ref", "enumId"):
        return "enum"
    if has_any_property(v, "calleePath", "callee", "selector", "selectorPath"):
        return "call_data"
    # tokenTicker only has chainId/chainIdPath - distinguish from other params that also have these fields
    if has_any_property(v, "chainId", "chainIdPath") and not has_any_property(
        v,
        "tokenPath",
        "token",
        "nativeCurrencyAddress",
        "threshold",
        "message",
        "types",
        "sources",
        "senderAddress",
    ):
        return "token_ticker"
    # addressName and interoperableAddressName have identical schemas (types, sources, senderAddress).
    # Default to address_name; the converter determines the actual type from the format field.
    if has_any_property(v, "types", "sources", "senderAddress"):
        return "address_name"
    return None


def visibility_rules_discriminator(v: Any) -> str | None:
    """
    Discriminator function for the VisibilityRules union type (v2).

    :param v: deserialized raw data
    :return: the discriminator tag
    """
    if isinstance(v, str):
        return "simple"
    if isinstance(v, dict) and has_any_property(v, "ifNotIn", "mustBe"):
        return "conditions"
    return None
