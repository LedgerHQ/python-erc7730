import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--skip-abi-validation",
        action="store_true",
        default=False,
        help="Skip Etherscan ABI validation in lint-related tests.",
    )


@pytest.fixture
def skip_abi_validation(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--skip-abi-validation"))
