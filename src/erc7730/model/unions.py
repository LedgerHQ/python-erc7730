from typing import Any

from erc7730.common.properties import has_property


def field_discriminator(v: Any) -> str | None:
    """
    Discriminator function for the Field union type.

    :param v: deserialized raw data
    :return: the discriminator tag
    """
    if has_property(v, "$ref"):
        return "reference"
    if has_property(v, "fields"):
        return "nested_fields"
    if has_property(v, "label"):
        return "field_description"
    return None


def field_parameters_discriminator(v: Any) -> str | None:
    """
    Discriminator function for the FieldParameters union type.

    :param v: deserialized raw data
    :return: the discriminator tag
    """
    if has_property(v, "tokenPath"):
        return "token_amount"
    if has_property(v, "encoding"):
        return "date"
    if has_property(v, "collectionPath"):
        return "nft_name"
    if has_property(v, "base"):
        return "unit"
    if has_property(v, "$ref") or has_property(v, "ref"):  # $ref is aliased
        return "enum"
    if has_property(v, "type"):
        return "address_name"
    if has_property(v, "selector"):
        return "call_data"
    return None
