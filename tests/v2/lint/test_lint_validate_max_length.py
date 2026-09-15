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
