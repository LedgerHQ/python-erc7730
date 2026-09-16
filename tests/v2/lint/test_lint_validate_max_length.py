import pytest

from erc7730.lint.v2.lint_validate_max_length import ValidateMaxLengthLinter
from erc7730.model.input.v2.format import VisibilityRule
from erc7730.model.paths.path_parser import to_path
from erc7730.model.resolved.v2.display import (
    ResolvedFieldDescription,
    ResolvedFieldGroup,
    ResolvedVisibilityConditions,
    ResolvedVisibilityRules,
)

# 28 characters, against the 20-character field name limit
LONG = "Referrer Config Basis Points"


def field(visible: ResolvedVisibilityRules | None) -> ResolvedFieldDescription:
    return ResolvedFieldDescription(label=LONG, path=to_path("#.referrerConfig.basisPoints"), visible=visible)


def collected(visible: ResolvedVisibilityRules | None) -> set[str]:
    out: set[str] = set()
    ValidateMaxLengthLinter._collect_long_labels(field(visible), out)
    return out


@pytest.mark.parametrize(
    "visible",
    [
        pytest.param(VisibilityRule.ALWAYS, id="always"),
        pytest.param(VisibilityRule.OPTIONAL, id="optional"),
        pytest.param(None, id="unset"),
        pytest.param(ResolvedVisibilityConditions(ifNotIn=["0"]), id="ifNotIn"),
    ],
)
def test_label_that_can_reach_a_screen_is_reported(visible: ResolvedVisibilityRules | None) -> None:
    """always, optional, unset and ifNotIn all display the field at least sometimes."""
    assert collected(visible) == {LONG}


@pytest.mark.parametrize(
    "visible",
    [
        pytest.param(VisibilityRule.NEVER, id="never"),
        pytest.param(ResolvedVisibilityConditions(mustMatch=["0"]), id="mustMatch"),
    ],
)
def test_label_that_never_reaches_a_screen_is_not_reported(visible: ResolvedVisibilityRules) -> None:
    """A hidden label cannot truncate, and a mustMatch field may legitimately carry no label."""
    assert collected(visible) == set()


def test_a_group_does_not_hide_the_labels_inside_it() -> None:
    """ResolvedFieldGroup carries no visibility of its own, so each child decides for itself."""
    group = ResolvedFieldGroup(fields=[field(VisibilityRule.NEVER), field(VisibilityRule.ALWAYS)])

    out: set[str] = set()
    ValidateMaxLengthLinter._collect_long_labels(group, out)

    assert out == {LONG}


@pytest.mark.parametrize(
    "intent,expected",
    [
        pytest.param("Withdraw {_amounts.[]}", 9, id="one_placeholder"),
        pytest.param("Send {sharesAmount} to {recipient}", 9, id="two_placeholders"),
        pytest.param("Stake ETH with SSV", 18, id="no_placeholder"),
        pytest.param("{_approved} unstETH NFTs", 13, id="leading_placeholder"),
    ],
)
def test_literal_length_counts_only_what_is_certain_to_be_displayed(intent: str, expected: int) -> None:
    """A `{path}` is template syntax, and the value replacing it has no length known here."""
    assert ValidateMaxLengthLinter._literal_length(intent) == expected


def test_a_long_path_inside_a_placeholder_does_not_make_the_intent_long() -> None:
    """`{execution.desc.minReturnAmount}` is 32 characters of path that never reaches a screen."""
    intent = "Swap for at least {execution.desc.minReturnAmount}"

    assert len(intent) > 30
    assert ValidateMaxLengthLinter._literal_length(intent) == 18


def test_literal_text_over_the_limit_is_still_measured() -> None:
    """Literal text alone over the limit truncates whatever the values render to."""
    intent = "Authorize decryption on behalf of {delegator} for {contracts} for {days} days"

    assert ValidateMaxLengthLinter._literal_length(intent) > 30
