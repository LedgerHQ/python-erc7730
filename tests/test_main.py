from pathlib import Path

import pytest
from typer.testing import CliRunner

from erc7730.main import app
from tests.cases import path_id
from tests.files import ERC7730_DESCRIPTORS, ERC7730_EIP712_DESCRIPTORS, LEGACY_EIP712_DESCRIPTORS

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    out = "".join(result.stdout.splitlines())
    assert "ERC-7730" in out
    assert "convert" in out
    assert "lint" in out


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_lint_registry_files(input_file: Path) -> None:
    result = runner.invoke(app, ["lint", str(input_file)])
    out = "".join(result.stdout.splitlines())
    assert str(input_file) in out
    assert any(
        (
            "no issues found ✅" in out,
            "some warnings found ⚠️" in out,
            "some errors found ❌" in out,
        )
    )


@pytest.mark.parametrize("input_file", LEGACY_EIP712_DESCRIPTORS, ids=path_id)
def test_convert_legacy_registry_eip712_files(input_file: Path, tmp_path: Path) -> None:
    result = runner.invoke(app, ["convert", "eip712-to-erc7730", str(input_file), str(tmp_path / input_file.name)])
    out = "".join(result.stdout.splitlines())
    assert "generated" in out
    assert "✅" in out


@pytest.mark.parametrize("input_file", ERC7730_EIP712_DESCRIPTORS, ids=path_id)
def test_convert_registry_files_to_legacy_eip712_files(input_file: Path, tmp_path: Path) -> None:
    result = runner.invoke(app, ["convert", "erc7730-to-eip712", str(input_file), str(tmp_path / input_file.name)])
    out = "".join(result.stdout.splitlines())
    assert "generated" in out
    assert "✅" in out
