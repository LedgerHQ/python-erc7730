from erc7730.common.abi import parse_signature
from erc7730.lint.v2.lint_validate_display_fields import ValidateDisplayFieldsLinter
from erc7730.model.abi import Function, InputOutput

# what the descriptor declares as its format key, naming every parameter
DECLARED = parse_signature("depositETH(address pool, address onBehalfOf, uint16 referralCode)")


def reference_abi(*names: str) -> Function:
    """Build the reference ABI of depositETH, in which unnamed parameters carry an empty name."""
    types = ["address", "address", "uint16"]
    return Function(
        name="depositETH",
        inputs=[InputOutput(name=name, type=type) for name, type in zip(names, types, strict=True)],
    )


def unnamed_parameter_names(abi: Function, declared_abi: Function | None = DECLARED) -> set[str]:
    return ValidateDisplayFieldsLinter._unnamed_parameter_names(abi, declared_abi)


def test_name_declared_at_an_unnamed_position_is_accepted() -> None:
    assert unnamed_parameter_names(reference_abi("", "onBehalfOf", "referralCode")) == {"pool"}


def test_name_declared_at_a_named_position_is_not_accepted() -> None:
    """`pool` is declared at position 0, which the reference ABI names `p`, so `#.pool` stays invalid."""
    assert unnamed_parameter_names(reference_abi("p", "", "referralCode")) == {"onBehalfOf"}


def test_no_name_is_accepted_when_the_reference_abi_names_every_parameter() -> None:
    assert unnamed_parameter_names(reference_abi("pool", "onBehalfOf", "referralCode")) == set()


def test_every_declared_name_is_accepted_when_the_reference_abi_names_nothing() -> None:
    assert unnamed_parameter_names(reference_abi("", "", "")) == {"pool", "onBehalfOf", "referralCode"}


def test_no_name_is_accepted_when_the_format_key_is_a_selector() -> None:
    assert unnamed_parameter_names(reference_abi("", "", ""), declared_abi=None) == set()
