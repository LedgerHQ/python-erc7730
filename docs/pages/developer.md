# Developer setup

## Prerequisites

This project uses [mise](https://mise.jdx.dev) to manage tool versions (Python, PDM, prek). Install mise first:

```bash
curl https://mise.run | sh
```

Or via Homebrew:

```bash
brew install mise
```

## Getting started

1. **Clone the repository:**

```bash
git clone --recursive git@github.com:LedgerHQ/python-erc7730.git
cd python-erc7730
```

2. **Install tools via mise:**

```bash
mise trust
mise install
```

This installs the correct versions of Python, [PDM](https://pdm-project.org) (package manager), and
[prek](https://github.com/j178/prek) (git hooks manager).

3. **Install project dependencies:**

```bash
pdm install --dev
```

4. **Install git hooks:**

```bash
prek install
```

## Common tasks

All project tasks are available as PDM scripts:

| Command | Description |
| --- | --- |
| `pdm run lint` | Run all linters/formatters via prek |
| `pdm run test` | Run the test suite |
| `pdm run docs` | Build documentation (output at `docs/build/index.html`) |
| `pdm run all` | Run lint + test |

## Linting

Linting is managed by [prek](https://github.com/j178/prek), a fast Rust-based drop-in replacement for
pre-commit. It uses the same `.pre-commit-config.yaml` configuration file.

```bash
pdm run lint
```

## Testing

```bash
pdm run test
```

By default, deprecated v1 tests and integration tests (full registry) are skipped. To include them:

```bash
pdm run test --run-v1           # include deprecated v1 tests
pdm run test --run-integration  # include integration tests against the full registry
```
