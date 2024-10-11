# Command line usage

## Installation

The `erc7730` tool is available as a [Python package on PyPI](https://pypi.org/project/erc7730). You can install it
using `pip`:

```bash
pip install --user erc7730
```

## Validation

You can validate your setup by running the `erc7730` command:

```{typer} erc7730.main.app
:preferred: svg
:theme: dark
:width: 100
:prog: erc7730
```

## Commands

### `erc7730 lint`

The `lint` command runs validations on descriptors and outputs warnings and errors to the console:
```shell
$ erc7730 lint registry
checking registry/lido/calldata-stETH.json...

checking registry/lido/calldata-wstETH.json...

checking registry/makerdao/eip712-permit-DAI.json...
DEBUG: Optional Display field missing: Display field for path `nonce` is missing for message Permit. If intentionally excluded, please add
it to `exclude` list to avoid this warning.
WARNING: Missing Display field: Display field for path `owner` is missing for message Permit. If intentionally excluded, please add it to
`exclude` list to avoid this warning.
```

It can be called with single files or directories, in which case all descriptors will be checked.

### `erc7730 convert`

The `convert` command converts descriptors between the ERC-7730 format and the legacy formats used by Ledger, for
instance:
```shell
$ erc7730 convert eip712-to-erc7730 ledger-asset-dapps/ethereum/1inch/eip712.json erc7730-eip712-1inch.json
generated erc7730-eip712-1inch.0x119c71d3bbac22029622cbaec24854d3d32d2828.json ✅
generated erc7730-eip712-1inch.0x111111125421ca6dc452d289314280a0f8842a65.json ✅
```

Please run `erc7730 convert --help` for more information on the available options.
