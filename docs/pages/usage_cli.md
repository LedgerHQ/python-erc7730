# Command line usage

## Installation

The `erc7730` tool is available as a [Python package on PyPI](https://pypi.org/project/erc7730). You can install it using `pip`:

```bash
pip install --user erc7730
```

Please note that the `erc7730` tool requires Python 3.12 or later. To ensure you are installing for the right python
version:
```bash
python3.12 -m pip install --upgrade erc7730
```

You can get the right python version for your system by using a version management tool such as
[mise](https://mise.jdx.dev), [asdf](https://asdf-vm.com), or [pyenv](https://github.com/pyenv/pyenv).

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
🔍 checking 61 descriptor files…

➡️ checking uniswap/eip712-UniswapX-ExclusiveDutchOrder.json…
no issue found ✔️

➡️ checking uniswap/eip712-uniswap-permit2.json…
⚪️ Optional Display field missing: No display field is defined for path `#.details.[].nonce` in message PermitBatch. If intentionally
excluded, please add it to `excluded` list to avoid this warning.
⚪️ Optional Display field missing: No display field is defined for path `#.details.nonce` in message PermitSingle. If intentionally
excluded, please add it to `excluded` list to avoid this warning.

➡️ checking tether/calldata-usdt.json…
🟠 warning: Function mismatch: Function approve(address,uint256) (selector: 0x095ea7b3) defined in descriptor ABIs does not match
reference ABI (see https://etherscan.io/address/0xdac17f958d2ee523a2206206994597c13d831ec7#code)
🟠 warning: Function mismatch: Function transfer(address,uint256) (selector: 0xa9059cbb) defined in descriptor ABIs does not match
reference ABI (see https://etherscan.io/address/0xdac17f958d2ee523a2206206994597c13d831ec7#code)
🔴 error: Invalid data path: "0xdAC17F958D2ee523a2206206994597C13D831ec7" is invalid, it must contain a data path to the address in the
transaction data. It seems you are trying to use a constant address value instead, please note this feature is not supported (yet).

checked 61 descriptor files, some errors found ❌
```

It can be called with single files or directories, in which case all descriptors will be checked.

### `erc7730 generate`

The `generate` bootstraps a new descriptor file from a template:
```shell
# fetch ABIs from etherscan and generate a new calldata descriptor
erc7730 generate --chain-id=1 --address=0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45

# generate a new calldata descriptor using given ABI file
erc7730 generate --chain-id=1 --address=0x0000000000000000000000000000000000000000 --abi abis.json

# generate a new EIP-712 descriptor using given schema file
erc7730 generate --chain-id=1 --address=0x0000000000000000000000000000000000000000 --schema schemas.json
```

To fetch ABIs automatically, you will need to [setup an Etherscan API key](https://docs.etherscan.io/getting-started/viewing-api-usage-statistics):
```shell
export ETHERSCAN_API_KEY=XXXXXX
```

Please note that while the generator does its best to guess the right format based on fields name/type, the generated
descriptor should be considered a starting point to refine.

### `erc7730 convert`

The `convert` command converts descriptors between the ERC-7730 format and the legacy formats used by Ledger, for
instance:
```shell
$ erc7730 convert eip712-to-erc7730 ledger-asset-dapps/ethereum/1inch/eip712.json erc7730-eip712-1inch.json
generated erc7730-eip712-1inch.0x119c71d3bbac22029622cbaec24854d3d32d2828.json ✅
generated erc7730-eip712-1inch.0x111111125421ca6dc452d289314280a0f8842a65.json ✅
```

Please run `erc7730 convert --help` for more information on the available options.

### `erc7730 resolve` / `erc7730 schema`

These commands allow to use descriptors in resolved form, which is a preprocessed form of the descriptor ready for
machine processing:
* Included documents have been inlined
* URLs have been fetched
* Contract addresses have been normalized to lowercase
* References have been inlined
* Constants have been inlined
* Field definitions have been inlined
* Nested fields have been flattened where possible
* Selectors have been converted to 4 bytes form

```shell
$ erc7730 schema                    # print JSON schema of input form (ERC-7730 specification)
$ erc7730 schema resolved           # print JSON schema of resolved form
$ erc7730 resolve <descriptor>.json # convert descriptor from input to resolved form
```
