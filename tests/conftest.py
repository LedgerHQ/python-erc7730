import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--skip-abi-validation",
        action="store_true",
        default=False,
        help="Skip reference ABI validation in lint-related tests.",
    )
    parser.addoption(
        "--run-v1",
        action="store_true",
        default=False,
        help="Run deprecated v1 tests (skipped by default).",
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests against the full registry (skipped by default).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "v1: mark test as v1 (deprecated, skipped unless --run-v1 is passed)")
    config.addinivalue_line(
        "markers", "integration: mark test as integration (skipped unless --run-integration is passed)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_v1 = config.getoption("--run-v1")
    run_integration = config.getoption("--run-integration")
    skip_v1 = pytest.mark.skip(reason="v1 tests are skipped by default (use --run-v1 to run)")
    skip_integration = pytest.mark.skip(
        reason="integration tests are skipped by default (use --run-integration to run)"
    )
    for item in items:
        if not run_v1 and "v1" in item.keywords:
            item.add_marker(skip_v1)
        if not run_integration and "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture
def skip_abi_validation(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--skip-abi-validation"))
