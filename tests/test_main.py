import json
from pathlib import Path
from shutil import copytree

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner, Result

from erc7730.main import app
from erc7730.model import ERC7730ModelType
from tests.cases import path_id
from tests.files import (
    ERC7730_DESCRIPTORS,
    ERC7730_EIP712_DESCRIPTORS,
    ERC7730_REGISTRY_ROOT,
    LEGACY_EIP712_DESCRIPTORS,
)

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


@pytest.mark.parametrize("model_type", list(ERC7730ModelType))
def test_schema_v2(model_type: ERC7730ModelType) -> None:
    result = runner.invoke(app, ["schema", model_type, "--v2"])
    out = "".join(result.stdout.splitlines())
    assert result.exit_code == 0
    assert json.loads(out) is not None


def test_schema_v2_reaches_the_v2_model() -> None:
    """Exit code 0 only proves a schema was printed, not which model it came from.

    `mustMatch` is a v2 visibility rule and `excluded` a v1 field, so each name appears
    in exactly one of the two schemas.
    """
    v1 = "".join(runner.invoke(app, ["schema", ERC7730ModelType.INPUT]).stdout.splitlines())
    v2 = "".join(runner.invoke(app, ["schema", ERC7730ModelType.INPUT, "--v2"]).stdout.splitlines())

    assert "excluded" in v1 and "mustMatch" not in v1
    assert "mustMatch" in v2 and "excluded" not in v2


def test_list() -> None:
    result = runner.invoke(app, ["list", str(ERC7730_REGISTRY_ROOT)])
    out = "".join(result.stdout.splitlines())
    assert "calldata-" in out
    assert "eip712-" in out
    assert ".json" in out


def test_format(tmp_path: Path) -> None:
    copytree(ERC7730_REGISTRY_ROOT, tmp_path / "registry")
    result = runner.invoke(app, ["format", str(tmp_path)])
    out = "".join(result.stdout.splitlines())
    assert "calldata-" in out
    assert "eip712-" in out
    assert ".json" in out
    assert "no errors occurred ✅" in out


# @pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
# def test_lint_registry_files(input_file: Path, skip_abi_validation: bool) -> None:
#     args = ["lint", str(input_file)]
#     if skip_abi_validation:
#         args.append("--skip-abi-validation")
#     result = runner.invoke(app, args)
#     out = "".join(result.stdout.splitlines())
#     assert str(input_file.name) in out
#     assert any(
#         (
#             "no errors found ✅" in out,
#             "some warnings found ⚠️" in out,
#             "some errors found ❌" in out,
#         )
#     )


@pytest.mark.integration
@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_resolve_registry_files(input_file: Path) -> None:
    result = runner.invoke(app, ["resolve", str(input_file)])
    out = "".join(result.stdout.splitlines())
    assert json.loads(out) is not None


@pytest.mark.parametrize(
    "label,chain_id,contract_address",
    [
        ("Uniswap v3 Router 2", 8453, "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"),
    ],
)
def test_generate_from_contract_address(label: str, chain_id: int, contract_address: str) -> None:
    result = runner.invoke(app, ["generate", f"--chain-id={chain_id}", f"--address={contract_address}"])
    out = "".join(result.stdout.splitlines())
    assert json.loads(out) is not None


@pytest.mark.integration
@pytest.mark.parametrize("input_file", LEGACY_EIP712_DESCRIPTORS, ids=path_id)
def test_convert_legacy_registry_eip712_files(input_file: Path, tmp_path: Path) -> None:
    result = runner.invoke(app, ["convert", "eip712-to-erc7730", str(input_file), str(tmp_path / input_file.name)])
    out = "".join(result.stdout.splitlines())
    assert "generated" in out
    assert "✅" in out


@pytest.mark.integration
@pytest.mark.parametrize("input_file", ERC7730_EIP712_DESCRIPTORS, ids=path_id)
def test_convert_registry_files_to_legacy_eip712_files(input_file: Path, tmp_path: Path) -> None:
    result = runner.invoke(app, ["convert", "erc7730-to-eip712", str(input_file), str(tmp_path / input_file.name)])
    out = "".join(result.stdout.splitlines())
    assert "generated" in out
    assert "✅" in out


CALLDATA_TEST_ADDRESS = "0x0000000000000000000000000000000000000001"
CALLDATA_TEST_UNKNOWN_CHAIN_ID = 987654321
CALLDATA_TEST_DEPOSIT_FORMATS = {
    "deposit(uint256 assets)": {
        "intent": "Deposit",
        "fields": [{"path": "assets", "label": "Amount", "format": "raw"}],
    }
}


def _calldata_v2_descriptor(chain_ids: list[int], metadata: dict, formats: dict) -> dict:
    return {
        "$schema": "https://eips.ethereum.org/assets/eip-7730/erc7730-v2.schema.json",
        "context": {
            "$id": "test",
            "contract": {"deployments": [{"chainId": c, "address": CALLDATA_TEST_ADDRESS} for c in chain_ids]},
        },
        "metadata": {"owner": "Test Owner", **metadata},
        "display": {"formats": formats},
    }


def _invoke_calldata(tmp_path: Path, descriptor: dict) -> Result:
    input_file = tmp_path / "calldata-test.json"
    input_file.write_text(json.dumps(descriptor))
    return runner.invoke(app, ["calldata", "--v2", str(input_file)])


def test_calldata_success_prints_only_json_on_stdout(tmp_path: Path) -> None:
    descriptor = _calldata_v2_descriptor(chain_ids=[1], metadata={}, formats=CALLDATA_TEST_DEPOSIT_FORMATS)

    result = _invoke_calldata(tmp_path, descriptor)

    assert result.exit_code == 0, result.output
    assert [d["chain_id"] for d in json.loads(result.stdout)] == [1]
    assert result.stderr == ""
    assert result.output == result.stdout


def test_calldata_warning_goes_to_stderr_and_keeps_stdout_json(tmp_path: Path) -> None:
    descriptor = _calldata_v2_descriptor(
        chain_ids=[1, CALLDATA_TEST_UNKNOWN_CHAIN_ID], metadata={}, formats=CALLDATA_TEST_DEPOSIT_FORMATS
    )

    result = _invoke_calldata(tmp_path, descriptor)

    assert result.exit_code == 0, result.output
    assert [d["chain_id"] for d in json.loads(result.stdout)] == [1]
    assert f"warning: Chain id {CALLDATA_TEST_UNKNOWN_CHAIN_ID} is not known" in result.stderr
    assert "warning" not in result.stdout
    assert "warning" in result.output


def test_calldata_conversion_error_goes_to_stderr_and_exits_1(tmp_path: Path) -> None:
    # a map key that cannot be encoded as a uint32 makes the selector fail to convert
    descriptor = _calldata_v2_descriptor(
        chain_ids=[1],
        metadata={"maps": {"tokens": {"values": {"4294967296": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"}}}},
        formats={
            "deposit(uint256 assets, uint32 marketId)": {
                "intent": "Deposit",
                "fields": [
                    {
                        "path": "assets",
                        "label": "Amount",
                        "format": "tokenAmount",
                        "params": {"token": {"map": "$.metadata.maps.tokens", "keyPath": "#.marketId"}},
                    }
                ],
            }
        },
    )

    result = _invoke_calldata(tmp_path, descriptor)

    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout) == []
    assert "error: Invalid map key" in result.stderr
    assert "Invalid map key" not in result.stdout
    assert "Invalid map key" in result.output


def test_calldata_invalid_descriptor_raises_and_exits_1(tmp_path: Path) -> None:
    descriptor = _calldata_v2_descriptor(chain_ids=[1], metadata={}, formats=CALLDATA_TEST_DEPOSIT_FORMATS)
    descriptor["display"] = "not an object"

    result = _invoke_calldata(tmp_path, descriptor)

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, ValidationError)
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.output == ""
