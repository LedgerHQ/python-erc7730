from dataclasses import dataclass
from pathlib import Path

from tests.files import ERC7730_REGISTRY, LEGACY_REGISTRY, PROJECT_ROOT


@dataclass(frozen=True, kw_only=True)
class TestCase:
    """Define a test case."""

    id: str
    label: str
    description: str
    error: str | None = None


def case_id(case: TestCase) -> str:
    """Generate test case identifier for a TestCase."""
    return case.id


def path_id(path: Path) -> str:
    """Generate test case identifier for a path."""
    for base in (ERC7730_REGISTRY, LEGACY_REGISTRY):
        if base in path.parents:
            return str(path.relative_to(base))
    return str(path.relative_to(PROJECT_ROOT))
