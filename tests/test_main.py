import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from erc7730.main import app
from erc7730.model import ERC7730ModelType
from tests.cases import path_id
from tests.files import ERC7730_DESCRIPTORS, ERC7730_EIP712_DESCRIPTORS, LEGACY_EIP712_DESCRIPTORS

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    out = "".join(result.stdout.splitlines())
    assert "ERC-7730" in out
    assert "convert" in out
    assert "lint" in out


@pytest.mark.parametrize("model_type", list(ERC7730ModelType))
def test_schema(model_type: ERC7730ModelType) -> None:
    result = runner.invoke(app, ["schema", model_type])
    out = "".join(result.stdout.splitlines())
    assert result.exit_code == 0
    assert json.loads(out) is not None


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_lint_registry_files(input_file: Path) -> None:
    result = runner.invoke(app, ["lint", str(input_file)])
    out = "".join(result.stdout.splitlines())
    assert str(input_file.name) in out
    assert any(
        (
            "no errors found ✅" in out,
            "some warnings found ⚠️" in out,
            "some errors found ❌" in out,
        )
    )


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_resolve_registry_files(input_file: Path) -> None:
    # TODO: these descriptors use literal constants instead of token paths, which is not supported yet
    if input_file.name in {"calldata-OssifiableProxy.json", "calldata-wstETH.json", "calldata-usdt.json"}:
        pytest.skip("Descriptor uses literal constants instead of token paths, which is not supported yet")

    result = runner.invoke(app, ["resolve", str(input_file)])
    out = "".join(result.stdout.splitlines())
    assert json.loads(out) is not None


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
