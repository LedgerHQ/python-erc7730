# Library usage

## Installation

The `erc7730` library is available as a [Python package on PyPI](https://pypi.org/project/erc7730). You can install it
using `pip`:

```bash
pip install --user erc7730
```

## Overview

A typical usage of the `erc7730` library is to load descriptors and compile them to a wallet manufacturer-specific
format:

```{mermaid}
---
title: Node
---
flowchart TD
   input_json@{ shape: doc, label: "ERC-7730 descriptor file" }
   input[input ERC-7730 descriptor]
   resolved[resolved ERC-7730 descriptor]
   vendor[wallet specific ERC-7730 descriptor]
   input_json -- load/validate --> input
   input -- resolve/validate --> resolved
   resolved -- convert --> vendor
```

## Packages

### `erc7730.model`

The `erc7730.model` package implements an object model mapping for ERC-7730 descriptors using
[pydantic](https://docs.pydantic.dev), allowing to easily read/write/transform descriptors.

#### input and resolved forms

Descriptors can be manipulated in 2 forms:
 - *"Input" form*: the descriptor document as defined in the ERC-7730 specification, after `include` tags have been
   resolved. It is possible to save back the descriptor back to the original descriptor document. 
 - *"Resolved" form*: the descriptor after pre-processing:
    - URLs have been fetched
    - Contract addresses have been normalized to lowercase
    - References have been inlined
    - Constants have been inlined
    - Field definitions have been inlined
    - Selectors have been converted to 4 bytes form
   This form is the most adapted to be used by tools and applications.

```{eval-rst}
.. autosummary::
 :nosignatures:
 
 erc7730.model.input.descriptor.InputERC7730Descriptor
 erc7730.model.resolved.descriptor.ResolvedERC7730Descriptor
```

#### input data model

```{eval-rst}
.. autopydantic_model:: erc7730.model.input.descriptor.InputERC7730Descriptor
 :noindex:
 :model-show-config-summary: False
 :model-show-field-summary: False
```

#### resolved data model

```{eval-rst}
.. autopydantic_model:: erc7730.model.resolved.descriptor.ResolvedERC7730Descriptor
 :noindex:
 :model-show-config-summary: False
 :model-show-field-summary: False
```

### `erc7730.lint`

The `erc7730.lint` package implements the `erc7730 lint` command. The main interface is `ERC7730Linter`:

```{eval-rst}
.. autoclass:: erc7730.lint.ERC7730Linter
 :members:
```

The package contains several linter implementations:

```{eval-rst}
.. autosummary::
 :nosignatures:
 
 erc7730.lint.lint_validate_abi.ValidateABILinter
 erc7730.lint.lint_validate_display_fields.ValidateDisplayFieldsLinter
 erc7730.lint.lint_transaction_type_classifier.ClassifyTransactionTypeLinter
```

### `erc7730.convert`

The `erc7730.convert` package implements the `erc7730 convert` command. The main interface is `ERC7730Converter`:

```{eval-rst}
.. autoclass:: erc7730.convert.ERC7730Converter
 :members:
```

The package contains several converter implementations:

```{eval-rst}
.. autosummary::
 :nosignatures:
 
 erc7730.convert.convert_erc7730_input_to_resolved.ERC7730InputToResolved
 erc7730.convert.convert_eip712_to_erc7730.EIP712toERC7730Converter
 erc7730.convert.convert_erc7730_to_eip712.ERC7730toEIP712Converter
```
