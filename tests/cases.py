from pathlib import Path

from tests.files import ERC7730_REGISTRY, LEGACY_REGISTRY, PROJECT_ROOT


def path_id(path: Path) -> str:
    """Generate test case identifier for a path."""
    for base in (ERC7730_REGISTRY, LEGACY_REGISTRY):
        if base in path.parents:
            return str(path.relative_to(base))
    return str(path.relative_to(PROJECT_ROOT))
