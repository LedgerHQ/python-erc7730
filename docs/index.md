python-erc7730
==============

**This library provides tooling for the ERC-7730 standard.**

See <https://github.com/LedgerHQ/clear-signing-erc7730-registry> for the standard specification and example descriptors.

This library implements:
 * Reading and writing ERC-7730 descriptor files into an object model
 * Validation, available as a command line tool
 * Conversion between Ledger specific legacy descriptors and ERC-7730

```{note}
The v1 schema is deprecated. New descriptors should use the v2 schema. The v1 model and linter are
retained for backward compatibility but will be removed in a future release.
```


```{toctree}
:maxdepth: 2
pages/usage_cli.md
pages/usage_library.md
pages/lint.md
pages/developer.md
```
